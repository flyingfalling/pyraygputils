# pyraygputils

GPU allocation/initialization/discovery utilities for ray cluster (python)

Package: pyraygputils

Richard Veale 2024

# TO INSTALL:

0) Install this package via pip in a virtual environment

   1) python3 -m venv /path/to/MYVENV

   2) source /path/to/MYENV/bin/activate

   3) pip install /path/to/pyraygputils

1) Install ansible (for ansible-playbook) via system package managers or
otherwise (e.g. pip install ansible)

2) Ensure you have a virtual environment with ray etc., installed
(this package will be installed in there anyways).

3) Create an inventory (see raystarter/inventories/example) for
ansible. Ensure that the global (all:vars) are set correctly,
e.g. rayvenvpath should point to THIS virtual environment (where this
package and ray is installed, it is needed to generate the ray
command). Make sure user specified has passwordless ssh access to the
hosts (e.g. via ssh key) (no sudo is needed)

Alternatively, manually point the variable raystartcmdgenerator to
execute the python script generate_ray_commands.py (e.g. set to
"python3 /path/to/generate_ray_commands.py").

# TO START RAY CLUSTER:

4) Execute ansible to start the ray cluster:
ansible-playbook -i /path/to/your/inventory /path/to/raystarter/playbooks/startray_ansible.yaml

TODO: make it so it copies a script to automatically run that, taking only a user -i argument?


# TO STOP RAY CLUSTER:

5) Stop the cluster using:
ansible-playbook -i /path/to/your/inventory /path/to/raystarter/playbooks/stopray_ansible.yaml



# TO USE GPU RESOURCE:

In your python script, include utilities from pyraygputils.pyraygputils (e.g. init_gpu_for_task).

At cluster init, it will automatically create per-node a custom ray resource gpu1gb, gpu2gb, ... gpuNNgb, which are the number of chunks of that memory size (1 GB, 4 GB, 10 GB) which will fit within a GPU of that system. For example, if a node has 2x 12GB GPUs (total 24GB VRAM), and your task requires 8GB memory, your node can run only 2 tasks at a time (one on each GPU), since the 8GB can not be split between the GPUs.

Currently, it does not handle requesting larger chunks (although you could request e.g. 4 gpu8gb if you wanted, and handle it yourself, it will correctly tell you the indices of the GPUs to use).

In the code, it will tell you the true indices of the GPUs (e.g. as shown via nvidia-smi, in PCI bus order) to use, and it will also set CUDA_VISIBLE_DEVICES=X for you, where X is the gpu ID. After that, most CUDA-using software will obey that (grabbing the first GPU visible, which will be the only one that is visible). If you request multiple, it may set CUDA_VISIBLE_DEVICES=X,Y,Z, in which case you must handle the devices to use yourself.

Note this package will select per-node the GPUs with the highest amount of memory up to the specified number of gpus (if you set ngpus=X in the ansible inventory for that node), and above a certain threshold (6GB per GPU, set in ansible inventory with GPUMINGB variable). So, a system may have a weak display GPU (e.g. 2GB nvidia P100), and stronger GPUs (e.g. 2x 16GB tesla P100). It will only select the 2 P100s (assuming GPUMINGB > 2). GPUMINGB is an integer, and it converts using base-10, so systems generally have e.g. 16.128GB or so of memory (for 16GB).

Note, everything currently only works with NVIDIA CUDA GPUs...

See examples/testray.py for an example of how to use utils for ray tasks.

See scripts/startray.py for an example of how to start a ray cluster so that the correct custom GPU resources are defined.


```
from pyraygputils.pyraygputils import init_gpu_for_task, raypool_from_resources;

#Create a ray pool with desired resources (including pergpu_gb in the resources dict, how many gpu mem you want per task in gigabytes):

ncpuper=4; #4cpu
memperproc=5e9; #5gb
pergpu_gb=4; #4gb vram per
mypool = raypool_from_resources( reqresources=dict(num_cpus=ncpuper, memory=memperproc,
                                                pergpu_gb=pergpu_gb),
						scheduling_strategy='SPREAD' );

#REV: your task function. In your worker task function (which will be farmed out by ray):
def yourfunct(idx):
    isready, gpuids, gpuresname = init_gpu_for_task();
    #do stuff
    return;

#REV: define list of tuples of your arguments to be passed to your function.
argslist = [(i,) for i in range(100)];

#Run your function on the pool using starmap (or map etc.)
reslist = list( mypool.starmap( yourfunct, argslist ) );

```