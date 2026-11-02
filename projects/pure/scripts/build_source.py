"""Shared Pure source builder; frozen P05 and P06 have separate output checks."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import copy
import hashlib
import json
from environment import PROJECT as R, OUTPUT, FONT_ROOT, BASELINE as BASE

EXPECTED = {
    "p05": "d2b50428d6ae56477178bdbfd99fb1a5cb128c8f38da4463d1ddfb433a22aa13",
    "p06": "12ac7406dbb255e20c682fa11c001ffa37cc626830f3b0310e2bb02554995fa7",
}


def build(version="p05", *, seed=None, output=None, field_suffixes=None):
    if version not in EXPECTED or (version == "p06" and seed is None):
        raise ValueError("P06 needs the freshly rebuilt P05 allocation seed")
    if not __debug__:
        raise RuntimeError("Frozen builder checks require Python without -O")
    original=BASE.read_bytes();assert hashlib.sha256(original).hexdigest()=='5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d'
    b=bytearray(original);patches=[];fields=[]
    spec=json.loads((R/'assets/translations_p05.json').read_text())
    if version == 'p06':
     if not isinstance(field_suffixes, dict) or set(field_suffixes) != {'0x91958', '0x91b2d'}:
      raise ValueError('P06 requires private field suffixes for its two adjusted prompts')
     for address, value in field_suffixes.items():
      if not isinstance(value, str): raise ValueError('Private field suffixes must be strings')
      spec['fields'][address][-1] = value
    font=ImageFont.truetype(str(FONT_ROOT/'fusion12/fusion-pixel-12px-monospaced-zh_hans.otf'),12)
    donors={g['character']:int(g['bitmap'],16)for g in json.loads((R/'assets/menu_glyphs.json').read_text())['glyphs']}
    def put(off,data,why):
     before=bytes(b[off:off+len(data)]);patches.append({'offset':off,'before':before.hex(),'after':data.hex(),'reason':why});b[off:off+len(data)]=data
    from ngp_localization.glyph12 import pack, unpack
    def charbits(ch):
     if ch==' ':return 0
     if 'A'<=ch<='Z':idx=ord(ch)-21
     elif '0'<=ch<='9':idx=ord(ch)-14
     elif ch in '【】':idx=122+'【】'.index(ch)
     else:idx=None
     if idx is not None:return unpack(original[0x10000+idx*18:0x10000+(idx+1)*18])
     if ch in donors:return donors[ch] >> 12
     im=Image.new('L',(12,12));ImageDraw.Draw(im).text((0,10),ch,font=font,anchor='ls',fill=255)
     bits=sum(1<<(143-y*12-x)for y in range(12)for x in range(12)if im.getpixel((x,y))>=128)
     assert bits or ch==' ',ch
     # The first display scanline is clipped by the original dialogue window.
     # Keep the font's original blank top row, as the Japanese bank does.
     return bits
    glyphs=copy.deepcopy(seed['glyphs']) if seed else []
    bybits={int(g['bitmap'],16):g['slot'] for g in glyphs}
    layout={f['original_offset']:(f['new_offset'],len(bytes.fromhex(f['payload_hex']))) for f in seed['fields']} if seed else {}
    def slot(bits,label):
     if bits not in bybits:
      i=len(glyphs);assert i<1000;bybits[bits]=i;glyphs.append({'slot':i,'label':label,'bitmap':bits.to_bytes(18,'big').hex(),'packed':pack(bits).hex()})
     return bybits[bits]
    def coded_slots(ids):
     out=bytearray();page=None
     for i in ids:
      p=48+i//128
      if p!=page:out.append(0xc0|p);page=p
      out.append(i%128)
     return bytes(out)
    def text(s):
     out=bytearray()
     for i,line in enumerate(s.split('\n')):
      assert len(line)<=12,(line,len(line))
      if i:out.append(0x81)
      out+=coded_slots([slot(charbits(c),c)for c in line])
     return bytes(out)
    def centered(s,width=60):
     ink=[]
     for i,c in enumerate(s):
      v=charbits(c);ink.extend((i*12+x,y)for y in range(12)for x in range(12)if v>>(143-y*12-x)&1)
     lo=min(x for x,y in ink);hi=max(x for x,y in ink);dx=(width-(hi-lo+1))//2-lo+3;cells=[0]*(width//12)
     for x,y in ink:xx=x+dx;cells[xx//12]|=1<<(143-y*12-xx%12)
     return coded_slots([slot(v,'centered:'+s)for v in cells])
    cursor=0xd0000
    def relocate(off,payload,description,clear=None):
     nonlocal cursor
     assert original[off]==0xfd
     end=original.index(0x80,off+1)+1
     if clear is None:clear=original[off+1]==0x83
     assert end-off>=4
     # The interpreter's verified opcode 02 is an absolute three-byte script jump.
     translated=bytes([0xfd])+(b'\x83'if clear else b'')+payload
     if original[end-2:end]==b'\x82\x80':translated+=b'\x82'
     translated+=b'\x80'
     padding=spec.get('demo_wait_padding',{}).get(hex(off),0)
     if padding:translated+=bytes([5,0x60|padding])
     translated+=b'\x02'+(0x200000+end).to_bytes(3,'little')
     if seed:
      at,capacity=layout[off]
      assert len(translated)<=capacity, 'Text exceeds frozen capacity'
      translated+=bytes(capacity-len(translated))
      cursor=at+capacity
     else:
      at=cursor;cursor+=len(translated)
     assert cursor<0xdf000
     assert original[at:cursor]==bytes(len(translated))
     put(at,translated,'relocated Chinese text: '+description)
     put(off,b'\x02'+(0x200000+at).to_bytes(3,'little'),'redirect text only: '+description)
     fields.append({'original_offset':off,'original_end':end,'new_offset':at,'text':description,'original_hex':original[off:end].hex(),'payload_hex':translated.hex()})
    # All four menu labels share the original five-character width; no asset redraw.
    payload=bytearray()
    for i,s in enumerate(spec['title'][:3]):payload+=b'\x87'+bytes([0x6a,0x60+i*3])+centered(s)+b'\x81'
    relocate(0x901a9,bytes(payload),'localized title menu entries 1-3')
    assert original[0x901e1]==0xfd
    relocate(0x901e1,b'\x87\x6a\x69'+centered(spec['title'][3]),'localized title extras entry',clear=False)
    for address,value in spec['fields'].items():
     off=int(address,16);end=original.index(0x80,off+2)+1;prefix=b''
     # Preserve the original per-letter speed where the opening specifies it.
     if original[off+2:off+3]==b'\x8c':prefix=original[off+2:off+4]
     parts=value if isinstance(value,list)else[value];payload=bytearray(prefix)
     for part in parts:payload+=text(part)if isinstance(part,str)else bytes.fromhex(part['hex'])
     relocate(off,bytes(payload),value if isinstance(value,str)else json.dumps(value,ensure_ascii=False))
    for g in glyphs:
     off=0xd3000+g['slot']*18;assert original[off:off+18]==bytes(18);put(off,bytes.fromhex(g['packed']),'Chinese bitmap: '+g['label'])
    from build_signature_p05 import build_signature
    signature=build_signature(original,put)
    # Load the saved original XBC; B itself is a scratch character register here.
    hook=bytearray.fromhex('a7 24');jumps=[]
    hook+=bytes.fromhex('ec cf 00 00 2d 00');jumps.append(len(hook));hook+=b'\x67\0'
    hook+=bytes.fromhex('ec cf 00 f0 2d 00');jumps.append(len(hook));hook+=b'\x6f\0'
    hook+=bytes.fromhex('db cf 00 18');jumps.append(len(hook));hook+=b'\x67\0'
    hook+=bytes.fromhex('44 00 80 2b 00 1b 0f 1c 20')
    for at in jumps:hook[at+1]=len(hook)-at-2
    hook+=bytes.fromhex('44 00 00 21 00 1b 0f 1c 20')
    assert 0xd3000+len(glyphs)*18<0xd4800
    assert original[0xd4800:0xd4800+len(hook)]==bytes(len(hook));put(0xd4800,hook,'context-scoped private-font selector')
    assert original[0x1c0a:0x1c0f]==bytes.fromhex('44 00 00 21 00');put(0x1c0a,bytes.fromhex('1b 00 48 2d 00'),'font selector entry')
    # Original shared menu setup is reached only after the slide animation.
    # Gate its dispatch wrapper by both the original script argument address and
    # the completed title text pointer, so other menus never receive the credit.
    wrapper=bytearray.fromhex('e9 cf d7 12 29 00');outer=len(wrapper);wrapper+=b'\x6e\0'
    wrapper+=b'\x3c'+bytes.fromhex('e1 56 42 24')
    completed=fields[0]['new_offset']+0x200000+len(bytes.fromhex(fields[0]['payload_hex']))
    wrapper+=bytes.fromhex('ec cf')+completed.to_bytes(4,'little');skip=len(wrapper);wrapper+=b'\x6e\0'
    wrapper+=b'\x1d'+(0x2d8000).to_bytes(3,'little')
    wrapper[skip+1]=len(wrapper)-skip-2
    wrapper+=b'\x5c';wrapper[outer+1]=len(wrapper)-outer-2
    wrapper+=bytes.fromhex('1b ac 14 20')
    assert original[0xd4900:0xd4900+len(wrapper)]==bytes(len(wrapper))
    put(0xd4900,wrapper,'post-transition title-menu credit dispatch wrapper')
    entry=0x18ce+0x20*4
    assert original[entry:entry+4]==(0x2014ac).to_bytes(4,'little')
    put(entry,(0x2d4900).to_bytes(4,'little'),'menu-ready dispatch entry; original handler retained')

    from build_title_p05 import build_title
    title_art=build_title(original,put)
    from build_status_art import build_assets
    cursor,status_art=build_assets(original,put,cursor)
    assert cursor<0xd3000
    D=Path(output) if output is not None else OUTPUT;D.mkdir(parents=True,exist_ok=True)
    name=f'Pure_{version.upper()}.ngc'
    from ngp_localization.paths import ensure_distinct_paths
    ensure_distinct_paths([BASE], [D/name, D/f'{version.upper()}_patch.json'])
    if hashlib.sha256(b).hexdigest()!=EXPECTED[version]:raise SystemExit(f'Output differs from frozen {version.upper()}; no frozen output written')
    (D/name).write_bytes(b)
    m={'base_sha256':hashlib.sha256(original).hexdigest(),'output_sha256':hashlib.sha256(b).hexdigest(),'rom_size':len(b),'changed_bytes':sum(x!=y for x,y in zip(original,b)),'patches':patches,'fields':fields,'glyphs':glyphs,'relocated_text_end':cursor,'new_font_end':0xd3000+len(glyphs)*18,'status_art':status_art}
    m['title_art']=title_art
    m['signature']=signature
    m['baseline_fix']='Cure donor bitmaps shifted down one pixel to match Fusion glyph baseline'
    (D/f'{version.upper()}_patch.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));print('fields',len(fields),'glyph tiles',len(glyphs),'changed',m['changed_bytes'],'sha',m['output_sha256'])

    return m
