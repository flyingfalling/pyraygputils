# pyraygputils
GPU allocation/initialization/discovery utilities for ray cluster (python)
Package: pyraygputils

Richard Veale 2024

TO INSTALL:

0) Install this package via pip in a virtual environment
   a) python3 -m venv /path/to/MYVENV
   b) source /path/to/MYENV/bin/activate
   c) pip install /path/to/pyraygputils

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

TO START RAY CLUSTER:

4) Execute ansible to start the ray cluster:
ansible-playbook -i /path/to/your/inventory /path/to/raystarter/playbooks/startray_ansible.yaml

#REV: todo: make it so it copies a script to automatically run that, taking only a user -i argument?


TO STOP RAY CLUSTER:

5) Stop the cluster using:
ansible-playbook -i /path/to/your/inventory /path/to/raystarter/playbooks/stopray_ansible.yaml



TO USE GPU RESOURCE:

In your python script, include utilities from pyraygputils.pyraygputils (e.g. init_gpu_for_task)

```
from pyraygputils.pyraygputils import init_gpu_for_task, raypool_from_resources;

#Create a ray pool with desired resources (including gpumem_gb in the resources dict, how many gpu mem you want per task in gigabytes):

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