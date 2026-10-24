"""Bounded provisional count, not a Unicode script extractor or route coverage proof."""
from collections import Counter
import hashlib,json
from environment import BASELINE

data=BASELINE.read_bytes()
if hashlib.sha256(data).hexdigest()!='5e304f68ca29fff2def6c5f4209224871156b9502f041d69129d025f0245428d':
 raise SystemExit('Wrong baseline')
lo,hi=0x93365,0xca682
controls={0x81:0,0x82:0,0x83:0,0x84:0,0x85:0,0x86:0,0x87:2,0x88:2,0x89:0,0x8a:0,0x8b:0,0x8c:1}
blocks=[];rejected=[];p=lo
while p<hi:
 if data[p]not in(0xfd,0xfe):p+=1;continue
 start=p;tag=data[p];p+=1;glyphs=[];page=0;valid=True
 while p<hi:
  value=data[p];p+=1
  if value==0x80:break
  if value<0x80:glyphs.append(page*128+value)
  elif value>=0xc0:
   if value in(0xfd,0xfe):valid=False;break
   page=value&63
  elif value in controls:p+=controls[value]
  else:valid=False;break
 else:valid=False
 if valid:blocks.append((tag,start,p,glyphs))
 else:rejected.append(hex(start))
dialogue=[x for x in blocks if x[0]==0xfe];unique=Counter(tuple(x[3])for x in dialogue)
print(json.dumps({'kind':'provisional static count only','range':[hex(lo),hex(hi)],'dialogue_records':len(dialogue),'nonempty_dialogue_records':sum(bool(x[3])for x in dialogue),'display_glyph_tokens':sum(len(x[3])for x in dialogue),'distinct_glyph_ids':len(set(g for x in dialogue for g in x[3])),'distinct_dialogue_token_strings':len(unique),'rejected_candidates':rejected,'note':'Contains names, spaces, punctuation and repeats. Does not decode Japanese Unicode or prove script reachability.'},ensure_ascii=False,indent=2))
