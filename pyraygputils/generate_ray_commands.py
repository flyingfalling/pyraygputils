import os;
import sys;
import argparse;
import re;
os.environ["RAY_DEDUP_LOGS"] = "0";
from ray.util.multiprocessing import Pool;
import ray;

def mb2gb(mb):
    return mb/1e3;


def resource_name_from_gpumem(gpumem):
    gpumem=int(gpumem);
    resourcename = "gpu{}gb".format(gpumem);
    return resourcename;


def select_single_gpu( gpuid ):
    isready=True;
    os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID";
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpuid);
    return isready;

def select_multiple_gpus( gpuidlist ):
    gpustr='';
    isready=False;
    if( gpuidlist ):
        asset = set(gpuidlist);
        if( len(asset) == 1 ):
            isready=True;
            pass;
        gpustr += ','.join( [str(id) for id in gpuidlist] ); #REV: it is a set
        #REV: this makes only relevant ones visible
        pass;
    os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID";
    os.environ["CUDA_VISIBLE_DEVICES"] = gpustr;
    return isready;




#REV: not hex...I think
def ray_get_node_resources( nodeip ):
    nodes = ray.nodes();
    for n in nodes:
        nodename=n['NodeName'];
        if( nodeip == nodename ):
            #print("FOUND IT!");
            #print(n['Resources']);
            return n['Resources'];
        pass;
    print(nodes);
    raise Exception("FAILED TO FIND nodename: [{}]".format(nodeip));


def ray_get_thisnode_resources():
    myip = ray.util.get_node_ip_address()
    return ray_get_node_resources(myip);


#REV: modify this to take a "gpumemperproc" argument. Assume it is PERGPU (not over all GPUs).
#REV: just define "singlegpu_memgb"
def raypool_from_resources( reqresources, **kwargs ):
    import ray;
    nodes=ray.nodes();
    rayfixed = dict(num_cpus='CPU', num_gpus='GPU', memory='memory');
    
    newresources=dict();
    totproc=0;

    gpumemtag = "pergpu_gb";
    if( gpumemtag in reqresources ):
        pergpu = reqresources[gpumemtag];
        reqresources.pop(gpumemtag);
        realname = resource_name_from_gpumem( pergpu );
        reqresources[realname] = 1; #REV: require 1 of these resources.
        print("CONVERTED per-gpu mem (GB) requested {} into requiring one {} resource".format(
            pergpu, realname ));
        #REV: need to make this so I can specify a "number" directly?
        pass;
    
    for n in nodes:
        nodename=n['NodeName'];
        nodeprocs=n['Resources']['CPU'];
        print( ("RAYPOOL from RESOURCES: NODE {}  "
                "DEFAULT PROCS=NCPU = {}".format(
                    nodename, nodeprocs)) );
        
        proclist=list([nodeprocs]);
        
        for reqresource in reqresources:
            if( reqresource in rayfixed ): ### FIXED RESOURCE
                fixres = reqresource;
                requestedval = reqresources[fixres];
                resourcename = rayfixed[fixres];
                realnames = [ k for k,v in n['Resources'].items()
                              if k.startswith(resourcename) ];
                
                if(len(realnames) > 1):
                    raise Exception(("REV: error found >1 keys "
                                     " in Resources "
                                     "of node {} beginning with "
                                     "{} (found {})".format(
                                         nodename, resourcename, realnames)));
                elif(len(realnames) < 1):
                    fitprocs=0;
                    realkey="NONE_ON_NODE";
                    pass;
                else:
                    realkey = realnames[0];
                    nodeval = n['Resources'][realkey];
                    fitprocs = int(nodeval / requestedval);
                    pass;
                print("    (NODE {}) FIXED RESOURCE: {} (Really {})  fits  {} procs".format(
                    nodename, resourcename, realkey, fitprocs));
                proclist.append(fitprocs);
                pass;
            else: ## NON FIXED RESOURCE
                requestedval = reqresources[reqresource];
                if( requestedval > 0 and reqresource in n['Resources'] ):
                    nodeval = n['Resources'][reqresource];
                    fitprocs = int(nodeval / requestedval); #REV: requested may be e.g. 0.5
                    pass;
                else:
                    nodeval = 0;
                    fitprocs = 0;
                    pass;
                print("    (NODE {}) CUSTM RESOURCE: {} (Really {})  fits  {} procs".format(
                    nodename, reqresource, reqresource, fitprocs));
                proclist.append(fitprocs);
                pass;
            pass;
        
        nodeprocs = min(proclist);
        print("  ++ FINAL RESULT -- NODE {}: [{}] procs".format(nodename, nodeprocs));
        totproc += nodeprocs;
        pass;
    
    resdict = dict();
    resdict['resources'] = dict();
    for reqresource in reqresources:
        if( reqresource in rayfixed ):
            #REV: handle "realname" here?
            resdict[reqresource] = reqresources[reqresource];
            pass;
        elif( reqresource == "pergpu_gb" ):
            requestedval = reqresources[reqresource];
            realname = resource_name_from_gpumem( requestedval );
            assert reqresources[realname]==1;
            resdict['resources'][realname] = reqresources[realname]; #REV: should be 1
            pass;
        else:
            resdict['resources'][reqresource] = reqresources[reqresource];
            pass;
        pass;

    myremoteargs = kwargs;
    myremoteargs.update(resdict);
    
    print("\nCREATING RAY POOL   {} PROCS\n(ARGS={})".format(
        totproc, myremoteargs));
    
    mypool = Pool(processes=totproc, ray_remote_args=myremoteargs);
    return mypool;


#REV: check sufficient memory is free to run my task (problem is I may be scheduling
# many simultaneously).
def check_gpu_runnable( gpuidx, requested_gpumem_gb ):
    isready=False;
    #REV: TODO
    #REV: GPUtils mb2gb(gpu.memoryFree())
    return isready;

def init_gpu_for_task( requested_gpumem_gb ):
    import ray;
    myrequestedresources = ray.get_runtime_context().get_assigned_resources();
    myresourceids = ray.get_runtime_context().worker.core_worker.resource_ids();
    
    resourcename=resource_name_from_gpumem(requested_gpumem_gb);
    #resourcename='gpu8gb'; #REV for example
    
    #REV: only works if env variable RAY_custom_unit_instance_resources is defined before
    #REV: start and contains in comma separated no space list this resource name
    #REV: this is just for getting "index" of this resource here.
    raycust = os.environ.get("RAY_custom_unit_instance_resources");
    print("INIT GPU -> {}".format(resourcename));
    rayindexed=raycust.split(",");
    if( resourcename in rayindexed ):
        myresourceidxs = myresourceids[ resourcename ]; #REV: this may be a LIST if e.g.
        #REV: I requested 4 gpu4gb...
        print("GOT MY GPU THREADIDXS: {}".format(myresourceidxs));
        pass;
    else:
        raise Exception("Unable to reliably confirm within-node ID of resource {}".format(resourcename));
    
    
    #REV: if it is GPU, I need to find true GPU index, by dividing (floor) by
    # number of GPUs on this system, then getting the index of the GPU and setting
    # NVIDIA_VISIBLE_DEVICES for it. Also check memoryFree. If heterogenous, search through
    # available.
    
    #REV: Unfortunately no good way to select. But I have ngpu, so I can assume it is the
    #REV: two HIGHEST
    os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID";
    #REV: I would use the values provided (set) by ray, but they may have not selected
    #REV: appropriate ones...(i.e. a weak display GPU versus a P100/A100).
    os.environ.pop('CUDA_VISIBLE_DEVICES', None);
    gpulist, memper = autodetect_gpus();
    
    #REV: determine which gpu "bin" I fall in.
    #REV: example 1: if 12, 16, and we are requesting gpu4gb,
    #REV: we will have 3, 4 each.
    #REV: we start with 6. (for 7 slots total)
    #REV: first, subtract 3, (now=3) (add currslot+=1, i.e. now 1)
    #REV: next subtract 4 (now=-1). RESULT: idx 1. (order in gpulist dict)
    #REV: example 2: let's say we just have 1.
    #REV: myidx = 0. numinme=1.

    #REV: make sure I only select the ngpu "best" gpus (determined by amount of VRAM)
    myresources = ray_get_thisnode_resources();
    if( 'GPU' in myresources ):
        ngpu = myresources['GPU'];
        #REV: we must remove the N lowest GPUs...
        #memlist = [ gpulist[k] for k in gpulist ];
        if( len(gpulist) != ngpu ):
            #REV: sort by value (tuples of (key,val)
            sortedgpus = sorted(gpulist.items(), key=lambda x:x[1]);
            aslist = [ gpulist[k] for k in gpulist ];
            if( aslist[-ngpu] == aslist[-(ngpu-1)] ):
                print(("REV: WARNING -- removing GPU of same memory "
                       "as accepted one, this is very weird [{}]".format(gpulist)));
                pass;
            goodgpus = sortedgpus[-ngpu:];
            gpulist = dict(goodgpus); #REV: tuple to dict works
            pass;
        pass;
    
    
    
    truegpuids=dict();
    
    for ridx in myresourceidxs:
        myidx = ridx[0]; #REV: is tuple (idx, proportion), e.g. (5, 0.5).
        proportion = ridx[1];
        #REV: multiply everything (all indices) by 1/proportion? NO, it is still telling
        #REV: me which PURE IDX to use (i.e. it will give me two (5, 0.5), three (5, 0.33).
        print("FINDING GPU IDX FOR THREADIDX {} (system has {} GPUs: {})".format(myidx, len(gpulist), gpulist));
        totalslots = myidx;
        for gpuid in gpulist:
            mymem = int(gpulist[gpuid]);
            numinme = mymem // requested_gpumem_gb;
            if( totalslots >= 0 ):
                totalslots -= numinme;
                pass;
            if( totalslots < 0 ):
                truegpuids[myidx] = gpuid;
                break;
            pass;
        pass;
    aslist = [ truegpuids[k] for k in truegpuids ];
    isready = select_multiple_gpus( aslist ); #REV: this sets CUDA_VISIBLE_DEVICES...
    
    #REV: user will have to handle it himself if I he needs to use multiple resources
    #REV: truegpuids are dict{ taskidx:pciorderedGPUidx }
    #REV: once CUDA_VISIBLE_DEVICES are set, need to refer to them as
    #REV: device 0, device 1, device 2 (i.e. will only select the visible ones)
    #REV: not original indices, which may be e.g. index 2,3 (ignoring 0,1).
    #REV: so 2 will be 0, 3 will be 1?
    return isready, truegpuids;





#REV: need a way to define GPU compute capability (only nvidia I guess)
#pip install nvidia-ml-py3
# REV; gets some raw stuff still no real ordering though for performance...
# 1) GPU memory
# 2) compute capability (e.g. NVIDIA 7.5 etc.?)
# 3) speed (ncudacores * hz/cudacore)
# 4) memory bus (net transfer capabilities)
# 5) current utilization (memory free)
#    -> REV: I can actually AUTO-DETECT GPUs with this script! No need to do ghetto
#       gpumem or etc...
def autodetect_gpus( mingpu_gb=6, mingpu_availgb=0 ):
    import GPUtil;
    validgpus=dict();
    try:
        GPUs = GPUtil.getGPUs();
        pass;
    except Exception: #REV: case where no NVIDIA installed on system (e.g. no driver)
        return validgpus, 0; 
    
    for gpu in GPUs:
        if(  mb2gb(gpu.memoryTotal) >= mingpu_gb and
             mb2gb(gpu.memoryFree) >= mingpu_availgb ):
            validgpus[gpu.id] = mb2gb(gpu.memoryTotal);
            pass;
        pass;
    
    pergpu_gb=0
    ngpu=len(validgpus);
    
    if( ngpu > 0 ):
        memlist = [validgpus[k] for k in validgpus];
        memval=memlist[0];
        for m in memlist[1:]:
            if( memval != m ):
                #print("REV: WARNING, multiple GPUs on system do not have identical GPU memory? Will use SMALLEST acceptable value ({})".format(memlist));
                pass;
            pass;
        pergpu_gb = min( memlist );
        pass;
    
    
    return validgpus, pergpu_gb; #ngpu, pergpu_gb;





def generate_ray_start_cmd(args):
    cmd = 'ray start';
    
    if( args.venv ):
        cmd = os.path.join(args.venv, 'bin', cmd);
        pass;
        
    commaseparatedresources='';
    port=args.port;
    if( args.ishead ):
        cmd += ' --head';
        pass;
    else:
        cmd += ' --address={}:{}'.format(args.headnode, args.port);
        pass;

    if( args.ishead ):
        cmd += ' --port={}'.format(port);
        pass
    
    if( args.ncpu ):
        cputag = ' --num-cpus={}'.format(args.ncpu);
        cmd+=cputag;
        pass;
    
    if not(args.ngpu):
        #args.ngpu, args.pergpu_gb = autodetect_gpus( );
        gpulist, args.pergpu_gb = autodetect_gpus( );
        args.ngpu = len(gpulist);
        args.pergpu_gb = int(args.pergpu_gb);
        args.gpulist = gpulist;
        pass;
    
    #REV: set NGPU even if it is 0, per node...
    gputag = ' --num-gpus={}'.format(args.ngpu);
    cmd+=gputag;
    
    
    if( args.venv and not os.path.exists(args.venv) ):
        #raise Exception("REV: ERROR, venv path does not exist on remote node {}".format(args.venv));
        #print("REV: WARNING, venv path does not exist on remote node {}".format(args.venv));
        pass;
    
    resourcesdict=dict();
    if( args.customresource ):
        for cr in args.customresource:
            #rtag = '{}={}'.format(cr[0], cr[1]);
            name=cr[0];
            namelist=name.split("_");
            if( namelist[0] != "raycustomresource" ):
                raise Exception("Defined custom resource must have form raycustomresource_NAME, and resource will be named NAME (NAME WAS {})".format(name));
            else:
                truename="_".join(namelist[1:]);
                resourcesdict[truename] = cr[1];
            pass;
        pass;
    
    #REV: possibly better parser?
    #https://github.com/neithere/argh/
    if( args.pergpu_gb ):
        if( not args.ngpu ):
            raise Exception('Must define ngpus if you define pergpu_gb');
        
        ###### Heterogenous GPU sizes on system (e.g. 12GB and 16GB on same node)
        if( args.gpulist ):
            howmany=0;
            for gpuid in args.gpulist:
                mymem = int(args.gpulist[gpuid]);
                for gb in range(1, (mymem+1)):
                    name = resource_name_from_gpumem(gb);
                    howmanyper = mymem // gb;
                    if name not in resourcesdict:
                        resourcesdict[name]=0;
                        pass;
                    resourcesdict[name] += howmanyper;
                    pass;
                pass;
            pass;
        else:
            ##### Homogenous GPUs on each system (or, assume so),
            #####   Even if 16GB and 12GB, will only use 12.
            for gb in range(1, (args.pergpu_gb+1)):
                name = resource_name_from_gpumem(gb);
                howmanyper = int(args.pergpu_gb) // gb;
                howmany = howmanyper * args.ngpu;
                resourcesdict[name] = howmany;
                pass;
            pass;
        pass;
    
    #print(resourcesdict);
    #REV: NEED DOUBLE ESCAPE TO PRINT \ backslash
    resourcestags=['\\"{}\\":{}'.format(k,v) for k,v in resourcesdict.items() ];
    #REV: double {{ }} for curly brace in string w/o format in python
    
    #REV: note can not have spaces or it will infer as another argument orz
    #REV: NEED THE ESCAPES HERE!!
    resourcestag = ' --resources=\{{{}\}}'.format(','.join(resourcestags));
    cmd += resourcestag;
    
    commaseparatedresources = ','.join( [ '{}'.format(k) for k in resourcesdict ] );
    prefix = 'export RAY_custom_unit_instance_resources=' + commaseparatedresources;
    cmd = prefix + " && " + cmd; #"'";
    return cmd;

def main():
    parser = argparse.ArgumentParser();
    parser.add_argument("--ishead",
                        action="store_true",
                        help="Pass for head node command (else will start worker)",
                        default=False  );
    parser.add_argument("--headnode", type=str, help="IP/hostname for head node");
    parser.add_argument("--port", type=str, help="Network port on which to communicate RAY", default=6379);
    parser.add_argument("--customresource", nargs=2, action='append', type=str, help="Add a custom resource");
    
    parser.add_argument("--pergpu_gb", type=int, help="GPU memory (in gigabytes) available per useable GPU (assumes homogenous GPU memory sizes on each node.). Only accepts whole numbers. If specified, will generate custom resources gpumemgb, gpu1gb, gpu2gb, gpu3gb, gpu4gb, gpu5gb...gpuXgb, where X is the largest gpu GB on this node. Later, calling generate_ray_pool() with desired GPU chunks will automatically add these custom resources. This will also reveal these custom variables to internal coreworker to get per-resource IDs so that we can determine (real) GPU index from them given per-node NUMGPUs and the init_gpus(gpugbpertask) function, which is run inside the task function to set appropriate CUDA_VISIBLE_DEVICES, and check other things like available GPU memory etc. I could also just read custom resource gpu2gb, etc., extract the number, and use that to split the GPU...I need to access node AVAILABLE resources, e.g. if node has resources gpu2gb=16 and ngpu=2, I assume that the first 8 resource ids are on gpu #0 and the later 8 on gpu #1 (with determination of proper useable GPUs accomplished by...what? Assume we can use all node GPUs by default, i.e. ignore any other CUDA_VISIBLE_DEVICES). Grab the GPUs with the correct amount of memory based on the gpu2gb=16 and ngpu=2, i.e. I expect to find 2 GPUs with at least 2*8=16GB, and select from among that up to 2 GPUs with the lowest current memory usage/GPU usage/temperature. I would like to select by COMPUTE CAPABILITY, but GPUtils does not offer that to me? Clock speed, number cores, generation, memory...");
    parser.add_argument("--venv", type=str, help="Virtual environment path for RAY");
    parser.add_argument("--ncpu", type=int, help="Set (override) num CPU of this node");
    parser.add_argument("--ngpu", type=int, help="Number of (useable) GPUs on the node");
    parser.add_argument("--memgb", type=int, help="Set (override) total mem (GB) of this node");
    args = parser.parse_args();

    if( args.customresource ):
        for i,cr in enumerate(args.customresource):
            args.customresource[i][1] = int(args.customresource[i][1]);
        pass;
    
    cmd = generate_ray_start_cmd(args);
    print(cmd, end="");
    
    return 0;

if __name__ == '__main__':
    exit(main());
    pass;
