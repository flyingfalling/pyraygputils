# pyraygputils
GPU allocation/initialization/discovery utilities for ray cluster (python)
Package: pyraygputils

Richard Veale 2024


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

4) Execute ansible to start the ray cluster:
ansible-playbook -i /path/to/your/inventory /path/to/raystarter/playbooks/startray_ansible.yaml

#REV: todo: make it so it copies a script to automatically run that, taking only a user -i argument?



5) Stop the cluster using:
ansible-playbook -i /path/to/your/inventory /path/to/raystarter/playbooks/stopray_ansible.yaml
