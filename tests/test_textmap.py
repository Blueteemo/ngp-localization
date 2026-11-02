import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from ngp_localization.textmap import decode_record, encode_record, load_mapping, _argument_end


class TextMapTests(unittest.TestCase):
    def test_controls_contain_opaque_terminator_and_entry_bytes(self):
        raw = bytes.fromhex('fe87e080e0fd88f080fe8ce080898080')
        record = decode_record(b'XX'+raw+b'ignored', offset=2, mapping={})
        self.assertEqual(encode_record(record), raw)
        self.assertEqual(record['end_offset'], 2+len(raw))

    def test_variable_operand_widths(self):
        for raw, size in [('60',1),('7e',1),('3036',2),('e078',2),('f080fe',3),('20',1),('50ff',2)]:
            self.assertEqual(_argument_end(bytes.fromhex(raw),0),size)
        r=decode_record(bytes.fromhex('fec0018ce0780285c0038ce078048c7e058580'),offset=0,mapping={1:'甲',2:'乙',3:'丙',4:'丁',5:'戊'})
        self.assertEqual(r['rendered_text'],'甲乙丙丁戊')
        self.assertEqual(r['unknown_glyph_ids'],[])

    def test_pages_render_and_unknowns(self):
        r = decode_record(bytes.fromhex('fdc10181c0020280'), offset=0, mapping={129:'甲'})
        self.assertEqual(r['rendered_text'], '甲\n[glyph:2][glyph:2]')
        self.assertEqual(r['unknown_glyph_ids'], [2])

    def test_invalid_records(self):
        for raw in [b'',b'\x00',b'\xfd',b'\xfd\x87\x80',b'\xfd\x88\x80',b'\xfd\x8c',b'\xfd\x8d\x80',b'\xfe\xfd\x80']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_record(raw, offset=0, mapping={})

    def test_tampering_and_trailing_bytes(self):
        original = decode_record(b'\xfe\xc1\x01\x80',offset=0,mapping={})
        variants=[]
        r=copy.deepcopy(original);r['raw_hex']+='00';r['end_offset']+=1;variants.append(r)
        r=copy.deepcopy(original);r['tokens'][2]['glyph_id']=1;variants.append(r)
        r=copy.deepcopy(original);r['tokens'][1]['offset']=2;variants.append(r)
        r=copy.deepcopy(original);r['tokens'][0]['opcode']=False;variants.append(r)
        for r in variants:
            with self.assertRaises(ValueError):encode_record(r)

    def test_mapping_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'map.json'
            for text in ['{"1":"a","01":"b"}','{"1":"a","1":"b"}','{"8192":"a"}','{"x":"a"}','{"1":""}','{"1":2}','[]']:
                p.write_text(text)
                with self.subTest(text=text),self.assertRaises(ValueError):load_mapping(p)
            p.write_text('{"0x81":"甲","2":"乙"}')
            self.assertEqual(load_mapping(p),{129:'甲',2:'乙'})

    def test_seeded_roundtrips(self):
        rng=random.Random(20261102)
        controls={0x81:0,0x82:0,0x83:0,0x84:0,0x85:0,0x86:2,0x87:2,0x88:1,0x89:-1,0x8a:0,0x8b:0,0x8c:1}
        for _ in range(500):
            raw=bytearray([rng.choice([0xfd,0xfe])])
            for _ in range(rng.randrange(35)):
                value=rng.choice([rng.randrange(128),rng.randrange(0xc0,0xfd),rng.choice(list(controls))])
                raw.append(value)
                count = controls.get(value, 0)
                if count == -1:
                    raw.append(rng.randrange(256))
                else:
                    for _ in range(count):
                        head = rng.randrange(256)
                        size = _argument_end(bytes([head,0,0]), 0)
                        raw.append(head)
                        raw.extend(rng.randrange(256) for _ in range(size-1))
            raw.append(0x80)
            r=decode_record(bytes(raw),offset=0,mapping={})
            self.assertEqual(encode_record(r),bytes(raw))

    def test_cli_preserves_input_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            rom=Path(d)/'input';out=Path(d)/'out.json';rom.write_bytes(b'X\xfe\x01\x80')
            command=[sys.executable,'-m','ngp_localization.textmap','--rom',str(rom),'--offset','1','--out',str(out)]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,2)
            self.assertEqual(rom.read_bytes(),b'X\xfe\x01\x80')
            self.assertEqual(json.loads(out.read_text())['records'][0]['start_offset'],1)


if __name__=='__main__':unittest.main()
