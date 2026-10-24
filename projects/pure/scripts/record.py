"""Continuous Beetle/Mednafen A/V capture, including black-background narration."""
from pathlib import Path
import json,subprocess,wave,hashlib,tempfile,ctypes,time
import numpy as np
from PIL import Image
from libretro_frontend import Core,BATCH
from environment import PROJECT as R, OUTPUT, EVIDENCE, ROM, BEETLE_CORE, BASELINE;D=EVIDENCE/'recording';D.mkdir(exist_ok=True)
rom=ROM
sha=hashlib.sha256(rom.read_bytes()).hexdigest();assert sha=='d2b50428d6ae56477178bdbfd99fb1a5cb128c8f38da4463d1ddfb433a22aa13'
ref=np.asarray(Image.open(EVIDENCE/'validation/med/title_prompt.png').convert('RGB'))
video=D/'capture_beetle_video.mp4';wav=D/'capture_beetle_audio.wav';out=D/'秋之回忆Pure_完整开场与菜单演示.mp4'
# Actual core raster/audio clock is 515 clocks x 199 lines at 6.144 MHz.
# Its libretro AV descriptor still advertises 60.25; using that value drifts
# ahead of the unmodified audio by about .42s across this recording.
fps='6144000/102485';fps_value=6144000/102485
encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','160x152','-framerate',fps,'-i','pipe:0','-an','-vf','scale=640:608:flags=neighbor','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-threads','2',str(video)],stdin=subprocess.PIPE)
samples=0;callbacks=0;landmarks=[];lastptr=None;title=None;press_at=None;final=None;wall=time.monotonic();narration=False
with tempfile.TemporaryDirectory()as save,wave.open(str(wav),'wb')as audio:
 audio.setnchannels(2);audio.setsampwidth(2);audio.setframerate(44100)
 c=Core(BEETLE_CORE,rom,Path(save))
 def batch(ptr,count):
  global samples,callbacks
  audio.writeframesraw(ctypes.string_at(ptr,count*4));samples+=count;callbacks+=1
  return count
 cb=BATCH(batch);c.lib.retro_set_audio_sample_batch(cb);c.callbacks.append(cb)
 for f in range(1,6501):
  held=press_at is not None and press_at<=f<press_at+3
  c.run(1,[0]if held else[]);rgb=np.asarray(c.frame.convert('RGB'));encoder.stdin.write(rgb.tobytes())
  ptr=int.from_bytes(c.memory()[0x256:0x25a],'little')
  if ptr!=lastptr:landmarks.append({'frame':f,'pointer':hex(ptr)});lastptr=ptr
  if f==196:
   narration=bool(np.sum(np.any(rgb[96:144,8:152]>100,axis=2))>100)
   assert narration,'First narration is missing';Image.fromarray(rgb).save(D/'narration.png')
  if title is None and f>3900 and np.array_equal(rgb,ref):
   title=f;press_at=f+90;final=press_at+360
   Image.fromarray(rgb).save(D/'title.png');print('Title reached:',title,'A at',press_at,flush=True)
  if f%600==0:print('Captured',f,'frames',flush=True)
  if final is not None and f>=final:
   Image.fromarray(rgb).save(D/'menu.png');break
 else:raise RuntimeError('Title prompt was not reached naturally')
 c.close()
encoder.stdin.close();assert encoder.wait()==0
video_seconds=f/fps_value;audio_seconds=samples/44100
assert narration and abs(video_seconds-audio_seconds)<.02,(video_seconds,audio_seconds)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(video),'-i',str(wav),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)],check=True)
with wave.open(str(wav),'rb')as a:pcm=np.frombuffer(a.readframes(a.getnframes()),dtype='<i2').reshape(-1,2)
blocks=[float(np.sqrt(np.mean(pcm[i:i+44100].astype(np.float64)**2)))for i in range(0,len(pcm),44100)]
assert max(blocks)>100 and sum(v>100 for v in blocks)>30
result={'rom_sha256':sha,'emulator':'Beetle/Mednafen NGP','real_hardware_recording':False,'from_reset':True,'uninterrupted':True,'gameplay_speed':'original raster clock, unmodified audio','video_fps':fps,'frames':f,'video_seconds':video_seconds,'audio_seconds':audio_seconds,'audio_sample_rate':44100,'audio_channels':2,'audio_callbacks_fully_consumed':callbacks,'black_background_narration_verified':True,'title_first_complete_frame':title,'A_pressed_frame':press_at,'A_hold_frames':3,'menu_hold_frames':360,'scale':'nearest neighbour 4x','audio_rms_each_second':blocks,'script_landmarks':landmarks,'audio_peak':int(np.max(np.abs(pcm.astype(np.int32)))),'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'wall_seconds':time.monotonic()-wall}
(D/'recording.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in ['audio_rms_each_second','script_landmarks']},ensure_ascii=False),flush=True)
