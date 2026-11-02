"""Synthetic-only tests: no ROM, font, Pillow or emulator needed."""
import copy
import importlib.util
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'projects/pure/scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('build_story_under_test', SCRIPTS / 'build_story.py')
story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story)
from ngp_localization.textmap import decode_record


class StoryBuilderTests(unittest.TestCase):
    def setUp(self):
        self.start = 0x1000
        self.raw = bytes.fromhex('fec00181c002828380')
        self.base = bytearray(story.BASE_SIZE)
        self.base[self.start:self.start+len(self.raw)] = self.raw
        self.old_hook = b'\xa7\x24' + bytes(31) + bytes.fromhex('44000021001b0f1c20')
        self.base[story.HOOK_START:story.HOOK_START+42] = self.old_hook
        for address, offsets in story.SAVE_ADDRESSES.items():
            for at in offsets: self.base[at:at+4] = address.to_bytes(4, 'little')
        for at, block in story.SAVE_ERASE_BLOCKS.items():
            self.base[at:at+4] = bytes([0xc7, 0x35, 0x03, block])
        self.base = bytes(self.base)
        self.record = decode_record(self.base, offset=self.start, mapping={})
        self.inventory = {'source_sha256': story.SOURCE_SHA, 'records': [self.record]}
        self.translations = [{'id': '0x1000', 'text': '甲\n乙{{82}}{{83}}'}]

    def plan(self, translations=None, selection=None, inventory=None, base=None):
        return story.prepare_plan(self.base if base is None else base,
                                  self.inventory if inventory is None else inventory,
                                  self.translations if translations is None else translations,
                                  [self.start] if selection is None else selection)

    def test_valid_plan_and_strict_control_page_resets(self):
        plan = self.plan()[0]
        encoded = story.encode_target(plan, {'甲': 1, '乙': 2})
        self.assertEqual(encoded[:9], bytes.fromhex('fec00181c002828380'))
        self.assertEqual(encoded[-4:], b'\x02' + (0x200000+plan['end']).to_bytes(3, 'little'))
        self.assertEqual(plan['line_widths'], [1,1,0])

    def test_controls_with_arguments_are_opaque_and_exact(self):
        raw = bytes.fromhex('fd87e080e0fe0188f082fd028ce0800380')
        record = decode_record(raw, offset=0, mapping={})
        events, checks = story.parse_target('{{87e080e0fe}}甲{{88f082fd}}乙{{8ce080}}丙', record)
        plan = {'entry': 0xFD, 'end': len(raw), 'events': events}
        encoded = story.encode_target(plan, {'甲':1,'乙':2,'丙':3})
        self.assertEqual(encoded[:-5], bytes.fromhex('fd87e080e0fec00188f082fdc0028ce080c003'))
        self.assertEqual(checks['widths'], [0,1,1,1])
        with self.assertRaises(ValueError):
            story.parse_target('{{87e080e0ff}}甲{{88f082fd}}乙{{8ce080}}丙', record)

    def test_preserves_fd_and_fe(self):
        for entry in (0xFD, 0xFE):
            plan = self.plan()[0]; plan['entry'] = entry
            self.assertEqual(story.encode_target(plan, {'甲':0,'乙':1})[0], entry)

    def test_rejects_changed_dropped_reordered_and_extra_controls(self):
        for text in ('甲\n乙', '甲\n乙{{83}}{{82}}', '甲\n乙{{82}}{{83}}{{84}}',
                     '甲\n乙{{8200}}{{83}}', '甲{{81}}乙{{82}}{{83}}', '甲\n乙{{8}}{{83}}',
                     '甲\n乙{82}{{83}}', '甲\n乙{{zz}}{{83}}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.plan([{'id':'0x1000','text':text}])

    def test_newline_and_line_limits_and_nonprinting(self):
        for text in ('甲乙{{82}}{{83}}', '甲\n\n乙{{82}}{{83}}', '甲'*13+'\n乙{{82}}{{83}}',
                     '甲\n乙\t{{82}}{{83}}', '甲\n\ud800{{82}}{{83}}'):
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                self.plan([{'id':'0x1000','text':text}])
        self.plan([{'id':'0x1000','text':'甲'*12+'\n乙{{82}}{{83}}'}])

    def test_ascii_and_full_width_spaces_are_visible_blank_glyphs(self):
        plan = self.plan([{'id':'0x1000','text':'甲 \u3000\n乙{{82}}{{83}}'}])[0]
        self.assertEqual(plan['line_widths'], [3,1,0])
        chars = story.collect_characters([plan])
        self.assertIn(' ', chars)
        self.assertIn('\u3000', chars)
        encoded = story.encode_target(plan, {char:i for i,char in enumerate(chars)})
        self.assertEqual(encoded[0], 0xFE)
        for illegal in ('\x00', '\r', '\t', '\u00a0', '\u200b', '\u202e', '\u2060', '\ud800'):
            with self.subTest(illegal=repr(illegal)), self.assertRaises(ValueError):
                self.plan([{'id':'0x1000','text':'甲'+illegal+'\n乙{{82}}{{83}}'}])

    def test_exact_selection_and_duplicate_normalization(self):
        for selected in ([], [self.start,'0x1000'], [True], [-1], ['1000'], [0x2000]):
            with self.subTest(selected=selected), self.assertRaises(ValueError):
                self.plan(selection=selected)
        for translations in ([], self.translations*2, self.translations+[{'id':'0x2000','text':''}],
                             [{'id':0x1000,'text':''}], [{'id':'0x01000','text':self.translations[0]['text']}, *self.translations]):
            with self.subTest(translations=translations), self.assertRaises(ValueError):
                self.plan(translations=translations)
        self.assertEqual(self.plan(selection=['0x1000'])[0]['start'], self.start)

    def test_rejects_non_candidate(self):
        with self.assertRaisesRegex(ValueError, 'not an inventory'):
            self.plan(translations=[{'id':'0x2000','text':''}], selection=[0x2000])

    def test_duplicate_inventory_and_wrong_source(self):
        inventory = copy.deepcopy(self.inventory); inventory['records'] *= 2
        with self.assertRaises(ValueError): self.plan(inventory=inventory)
        inventory = copy.deepcopy(self.inventory); inventory['source_sha256'] = '0'*64
        with self.assertRaises(ValueError): self.plan(inventory=inventory)

    def test_source_bytes_and_token_tampering(self):
        base = bytearray(self.base); base[self.start+2] = 3
        with self.assertRaises(ValueError): self.plan(base=bytes(base))
        inventory = copy.deepcopy(self.inventory); inventory['records'][0]['tokens'][2]['glyph_id'] = 10
        with self.assertRaises(ValueError): self.plan(inventory=inventory)

    def test_short_and_overlapping_source_records(self):
        for raw, starts in ((bytes.fromhex('fe0180'), [0]), (bytes.fromhex('fe87e0fe61c00180'), [0,3])):
            inventory = {'source_sha256':story.SOURCE_SHA,
                         'records':[decode_record(raw,offset=i,mapping={}) for i in starts]}
            translations = [{'id':hex(i),'text':'{{87e0fe61}}甲' if i==0 and len(starts)>1 else '甲'} for i in starts]
            with self.assertRaises(ValueError):
                story.prepare_plan(raw, inventory, translations, starts)

    def test_stable_sorted_slots_and_safe_page_limit(self):
        plans = self.plan()
        self.assertEqual(story.collect_characters(plans), sorted(['甲','乙']))
        plan = plans[0]
        self.assertIn(bytes([0xFC,127]), story.encode_target(plan, {'甲':7807,'乙':0}))
        with self.assertRaises(ValueError): story.encode_target(plan, {'甲':7808,'乙':0})
        huge = [{'events':[('glyph',chr(0xE000+i)) for i in range(7809)]}]
        with self.assertRaises(ValueError): story.collect_characters(huge)

    def test_hook_preserves_fallback_and_jumps_to_old_logic(self):
        hook = story.expansion_hook(self.old_hook)
        self.assertEqual(len(hook), 67)
        self.assertEqual(hook[27:], self.old_hook[2:])
        self.assertEqual(8+2+hook[9], 27)
        self.assertEqual(16+2+hook[17], 27)
        for old in (self.old_hook[:40], b'xx'+self.old_hook[2:], self.old_hook[:-1]+b'x'):
            with self.assertRaises(ValueError): story.expansion_hook(old)

    def test_assembly_changes_only_targets_hook_save_layout_and_expansion(self):
        plans = self.plan(); chars = story.collect_characters(plans)
        result, report = story.build_image(self.base, plans, chars, bytes(18*len(chars)))
        self.assertEqual(len(result), 0x200000)
        self.assertEqual(result[self.start:self.start+4], bytes.fromhex('02000030'))
        self.assertEqual(result[self.start+4:self.start+len(self.raw)], self.raw[4:])
        self.assertEqual(result[story.TEXT_START], 0xFE)
        self.assertEqual(report['record_count'],1)
        self.assertEqual(report['records'][0]['line_widths'],[1,1,0])
        self.assertEqual(report['changed_ranges'][-1], {'start':0x100000,'end':0x200000,'kind':'added'})
        allowed = set(range(self.start,self.start+4)) | set(range(story.HOOK_START,story.HOOK_START+67))
        for offsets in story.SAVE_ADDRESSES.values():
            for at in offsets: allowed.update(range(at, at+4))
        for at in story.SAVE_ERASE_BLOCKS: allowed.update(range(at, at+4))
        self.assertEqual(result[story.SAVE_START:], b'\xff'*0x10000)
        self.assertEqual(len(report['save_layout']['patches']),25)
        self.assertTrue(all(a==b or i in allowed for i,(a,b) in enumerate(zip(self.base,result))))
        self.assertEqual(self.base[self.start:self.start+len(self.raw)], self.raw)

    def test_capacity_and_hook_padding_guards(self):
        plans=self.plan(); chars=story.collect_characters(plans); bank=bytes(len(chars)*18)
        with patch.object(story,'TEXT_LIMIT',story.TEXT_START+5), self.assertRaises(ValueError):
            story.build_image(self.base,plans,chars,bank)
        with patch.object(story,'ROM_SIZE',story.FONT_START+len(bank)), self.assertRaises(ValueError):
            story.build_image(self.base,plans,chars,bank)
        base=bytearray(self.base);base[story.HOOK_START+42]=1
        with self.assertRaises(ValueError): story.build_image(bytes(base),plans,chars,bank)
        with self.assertRaises(ValueError): story.build_image(self.base,plans,list(reversed(chars)),bank)

    def test_save_layout_checks_every_operand_and_reserves_factory_flash(self):
        source = self.base + bytes(story.BASE_SIZE)
        result, changes = story.expand_save_layout(source)
        self.assertEqual(len(changes),25)
        for old, offsets in story.SAVE_ADDRESSES.items():
            for at in offsets:
                self.assertEqual(result[at:at+4], (old+0x100000).to_bytes(4,'little'))
                bad=bytearray(source);bad[at] ^= 1
                with self.assertRaises(ValueError):story.expand_save_layout(bytes(bad))
        for at, block in story.SAVE_ERASE_BLOCKS.items():
            self.assertEqual(result[at:at+4], bytes([0xc7,0x35,0x03,block+16]))
            bad=bytearray(source);bad[at+3] ^= 1
            with self.assertRaises(ValueError):story.expand_save_layout(bytes(bad))
        bad=bytearray(source);bad[story.SAVE_START]=0x80
        with self.assertRaises(ValueError):story.expand_save_layout(bytes(bad))
        with self.assertRaises(ValueError):story.expand_save_layout(result) # not idempotent
        self.assertEqual(source[self.start:self.start+len(self.raw)],self.raw)

    def test_clear_resets_line_and_positioned_controls_bound_segments(self):
        raw = bytes.fromhex('fec0018381c002828380')
        record = decode_record(raw, offset=0, mapping={})
        _, checks = story.parse_target('甲'*12+'{{83}}\n'+'乙'*12+'{{82}}{{83}}', record)
        self.assertEqual(checks['widths'], [12,0,12,0])
        record = decode_record(bytes.fromhex('fe876060c00102876160c00380'), offset=0, mapping={})
        _, checks = story.parse_target('{{876060}}甲{{876160}}乙', record)
        self.assertEqual(checks['mode'],'positioned_source_segments')
        self.assertEqual(checks['limits'], [0,2,1])
        with self.assertRaises(ValueError):
            story.parse_target('{{876060}}甲{{876160}}乙丙', record)

    def test_half_width_line_limit_uses_source_not_an_unlimited_exemption(self):
        raw = b'\xfe\x8b\xc0' + bytes([1])*16 + b'\x80'
        record = decode_record(raw, offset=0, mapping={1:'A'})
        _, checks = story.parse_target('{{8b}}'+'A'*16, record)
        self.assertEqual(checks['mode'],'source_half_width_lines')
        self.assertEqual(checks['limits'], [16])
        self.assertEqual(checks['ascii_sequence_validation'], 'unchanged_long_ascii_lines')
        with self.assertRaises(ValueError): story.parse_target('{{8b}}'+'甲'*16,record)
        short = decode_record(bytes.fromhex('fec0018b0280'), offset=0, mapping={1:'A',2:'B'})
        with self.assertRaisesRegex(ValueError, 'narrow'): story.parse_target('甲{{8b}}乙', short)
        story.parse_target('A{{8b}}乙', short)
        indirect = decode_record(bytes.fromhex('fec0018ce03c8b0280'), offset=0, mapping={1:'A',2:'B'})
        with self.assertRaisesRegex(ValueError, 'narrow'): story.parse_target('甲{{8ce03c}}{{8b}}乙', indirect)
        with self.assertRaises(ValueError): story.parse_target('{{8b}}'+'B'*16,record)
        with self.assertRaises(ValueError): story.parse_target('{{8b}}'+'A'*17,record)

    def test_input_set_rejects_mixed_generation(self):
        import hashlib, json
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {name: root/name for name in ('inventory','translations','selection')}
            for path in paths.values(): path.write_bytes(b'[]')
            pin = root/'input-set.json'
            pin.write_text(json.dumps({name: hashlib.sha256(path.read_bytes()).hexdigest()
                                       for name,path in paths.items()}), encoding='utf-8')
            snapshots, digest = story.read_input_set(pin, paths)
            self.assertEqual(set(snapshots), set(paths))
            paths['translations'].write_bytes(b'[1]')
            with self.assertRaisesRegex(ValueError, 'generation'):
                story.read_input_set(pin, paths)
            pin.write_text('{}', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'exactly'):
                story.read_input_set(pin, paths)

    def test_cli_invalid_input_never_creates_output_or_requires_pillow(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); rom=root/'original';rom.write_bytes(b'synthetic-not-P06')
            source=root/'input.json';source.write_text('{}');output=root/'new-output'
            command=[sys.executable,'-S',str(SCRIPTS/'build_story.py'),'--rom',str(rom),'--input-set',str(source),
                     '--inventory',str(source),'--translations',str(source),'--selection',str(source),'--out',str(output)]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertIn('frozen P06',result.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(rom.read_bytes(),b'synthetic-not-P06')

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'input.json';path.write_text('{"records":[],"records":[]}')
            with self.assertRaises(ValueError): story.read_json(path)


if __name__ == '__main__':
    unittest.main()
