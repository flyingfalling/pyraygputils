import sys;
import os;
import re;
os.environ["RAY_DEDUP_LOGS"] = "0";
import ray;
import cv2;

from pyraygputils.pyraygputils import *;


def checkgpustuff(myidx):
    isready, gpuids, gpures = init_gpu_for_task();
    print("Initialized GPU! (RES: {}   IDS: {})".format(gpures, gpuids));
    return;


def main():
    rayvenv='/home/rveale/venvs/rayvenv/';
    print("Initializing ray with VENV={}".format(rayvenv));
    runtime_env = { "env_vars":
                    { "VIRTUAL_ENV": rayvenv,
                      "PATH": os.path.join(rayvenv,'bin') + ":$PATH" },
                   };
    
    ray.init(address='auto', runtime_env=runtime_env);
    
    print(ray.nodes());
    
    ncpuper=4;
    memperproc=5e9;
    #gpuper=1; #0.25; #REV: specify both GPU per and also TYPE of gpu (gpu memory vram!)
    #gpu16per=1;
    #gpumemper=16;
    pergpu_gb=4;
    
    with raypool_from_resources( reqresources=dict(num_cpus=ncpuper,
                                                pergpu_gb=pergpu_gb,
                                                memory=memperproc),
                                 scheduling_strategy='SPREAD' ) as mypool:
        argslist = [(i,) for i in range(100)];
        reslist = list( mypool.starmap( checkgpustuff, argslist ) );
        pass;
    
    return 0;

if __name__=='__main__':
    exit(main());
    
