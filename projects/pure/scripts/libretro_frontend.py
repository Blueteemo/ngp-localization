"""Minimal libretro frontend for reproducible NGPC frame/input/state capture."""
import ctypes as C
from pathlib import Path
import numpy as np
from PIL import Image
class GameInfo(C.Structure):
 _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Variable(C.Structure):
 _fields_=[('key',C.c_char_p),('value',C.c_char_p)]
ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUDIO=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
POLL=C.CFUNCTYPE(None)
INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
class Core:
 def __init__(self,core,rom,save_dir):
  self.lib=C.CDLL(str(Path(core).resolve()));self.frame=None;self.frames=0;self.pixel=0;self.capture_this_frame=True;self.buttons=set();self.callbacks=[];self.env_seen=set()
  self.path=str(Path(rom).resolve()).encode();self.save=str(Path(save_dir).resolve()).encode();Path(save_dir).mkdir(parents=True,exist_ok=True)
  self.values={b'ngp_language':b'japanese'}
  def env(cmd,data):
   self.env_seen.add(cmd)
   if cmd in (9,31):C.cast(data,C.POINTER(C.c_char_p))[0]=self.save;return True
   if cmd==10:self.pixel=C.cast(data,C.POINTER(C.c_uint))[0];return True
   if cmd==15:
    v=C.cast(data,C.POINTER(Variable)).contents
    if v.key in self.values:v.value=self.values[v.key];return True
    return False
   if cmd==17:C.cast(data,C.POINTER(C.c_bool))[0]=False;return True
   if cmd==52:C.cast(data,C.POINTER(C.c_uint))[0]=0;return True
   if cmd==39:C.cast(data,C.POINTER(C.c_uint))[0]=0;return True
   if cmd==2:C.cast(data,C.POINTER(C.c_bool))[0]=False;return True
   if cmd==3:C.cast(data,C.POINTER(C.c_bool))[0]=True;return True
   if cmd in (6,8,11,16,18,32,37,53,67):return True
   return False
  def video(data,w,h,pitch):
   if not data or not self.capture_this_frame:return
   raw=C.string_at(data,pitch*h)
   if self.pixel==1:
    a=np.frombuffer(raw,np.uint8).reshape(h,pitch)[:,:w*4].reshape(h,w,4)
    a=a[:,:,[2,1,0]]
   else:
    a=np.frombuffer(raw,np.uint16).reshape(h,pitch//2)[:,:w]
    if self.pixel==2:
     r=(a>>11)&31;g=(a>>5)&63;b=a&31;a=np.stack([r*255//31,g*255//63,b*255//31],axis=2).astype(np.uint8)
    else:
     r=(a>>10)&31;g=(a>>5)&31;b=a&31;a=np.stack([r*255//31,g*255//31,b*255//31],axis=2).astype(np.uint8)
   self.frame=Image.fromarray(a.copy(),'RGB')
  def state(port,device,index,button):return int(port==0 and button in self.buttons)
  callbacks=[('retro_set_environment',ENV(env)),('retro_set_video_refresh',VIDEO(video)),('retro_set_audio_sample',AUDIO(lambda l,r:None)),('retro_set_audio_sample_batch',BATCH(lambda p,n:n)),('retro_set_input_poll',POLL(lambda:None)),('retro_set_input_state',INPUT(state))]
  for name,cb in callbacks:
   fn=getattr(self.lib,name);fn.argtypes=[type(cb)];fn(cb);self.callbacks.append(cb)
  self.lib.retro_init()
  self.rom=C.create_string_buffer(Path(rom).read_bytes());info=GameInfo(self.path,C.cast(self.rom,C.c_void_p),len(self.rom)-1,None)
  self.lib.retro_load_game.argtypes=[C.POINTER(GameInfo)];self.lib.retro_load_game.restype=C.c_bool
  if not self.lib.retro_load_game(C.byref(info)):raise RuntimeError('ROM load failed')
  self.lib.retro_get_memory_size.argtypes=[C.c_uint];self.lib.retro_get_memory_size.restype=C.c_size_t
  self.lib.retro_get_memory_data.argtypes=[C.c_uint];self.lib.retro_get_memory_data.restype=C.c_void_p
  self.lib.retro_serialize_size.restype=C.c_size_t
  self.lib.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];self.lib.retro_serialize.restype=C.c_bool
  self.lib.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];self.lib.retro_unserialize.restype=C.c_bool
 def run(self,n,buttons=()):
  self.buttons=set(buttons)
  for i in range(n):
   self.capture_this_frame=(i==n-1);self.lib.retro_run();self.frames+=1
  return self.frame
 def press(self,button=8,n=3,after=60):
  self.run(n,[button]);return self.run(after)
 def screenshot(self,path):
  if self.frame is None:raise RuntimeError('No video frame')
  self.frame.save(path)
 def memory(self,kind=2):
  p=self.lib.retro_get_memory_data(kind);n=self.lib.retro_get_memory_size(kind)
  return C.string_at(p,n) if p and n else b''
 def save_state(self,path):
  n=self.lib.retro_serialize_size();b=C.create_string_buffer(n)
  if not self.lib.retro_serialize(b,n):raise RuntimeError('Serialize failed')
  Path(path).write_bytes(b.raw)
 def load_state(self,path):
  b=Path(path).read_bytes();buf=C.create_string_buffer(b)
  if not self.lib.retro_unserialize(buf,len(b)):raise RuntimeError('Unserialize failed')
 def close(self):self.lib.retro_unload_game();self.lib.retro_deinit()
