#!/bin/sh

#Tool to install ansible pre-requisites to provision a cluster for CICaDa
#Note:
#(i)  From CICaDa >=6.4 RHEL 9.4  support added
#(ii) RHEL clusters should be subscription activated.
##############################################################################################################################
#Usage:
#
#In 'master' vm execute:
#source pre-req-installer.sh master
#
#In 'worker' vm execute:
#source pre-req--installer.sh worker
#
#Chronyd(NTP) service is used for Time sync in Cluster
#Fot NTP check optionally execute on relevant vm as
#
#source pre-req-installer.sh master ntp
#
#Works only on these OpenStack Flavors:
#-------------------------------------
#CentOS-7-x86_64-GenericCloud-2009
#rhel-server-7.9-update-12-x86_64-kvm.qcow2
#rhel-8.6-x86_64-kvm-2022-05-11.qcow2
#rhel-8.8-x86_64-kvm.qcow2
#Ubuntu-LTS-20.04.qcow2
#CentOS-Stream-GenericCloud-8-20220913.0.x86_64.qcow2
#OL8U8_x86_64-kvm-b198.qcow2
#############################################################################################################################

#Variables
ntp_check=false
py_ver=3.6
py_pip_ver="python36-pip"

arg_2=$(echo $2 | tr '[:upper:]' '[:lower:]')
ntp_str="Running pre-requisites installer with 'ntp'"
[ "$arg_2" = "ntp" ] && { ntp_check=true; echo "$ntp_str $ntp_check ";} || { ntp_check=false; echo "$ntp_str $ntp_check. If 'ntp' check required, run as pre-reqinstaller.sh master ntp"; }

#Function to ###############  detect OS version #################################
check_os_distribution()
{
py_arr={}
#echo "py_arr $py_Arr"
os_distro=$(cat /etc/*release   | grep PRETTY_NAME |sed 's/PRETTY_NAME=//g'| tr -d '"')

#echo "------OS distro detected: $os_distro-------------"
case "$os_distro" in
        "Red Hat Enterprise Linux 8.6"*) install_CStm_RHEL_OL_pre_reqs $1 python39-pip python3.9;
                ;;
        "Red Hat Enterprise Linux 8.8"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
                ;;
        "Red Hat Enterprise Linux 8.10"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
                ;;
        "Red Hat Enterprise Linux 9"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
		;;
        "Red Hat Enterprise Linux 9.4"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
		;;
        "CentOS Stream 8"*) install_CStm_RHEL_OL_pre_reqs $1 python39-pip python3.9;
                ;;
        "CentOS Linux 7"*) install_CStm_RHEL_OL_pre_reqs $1 python36-pip python3.6;
                ;;
        "Red Hat Enterprise Linux Server 7.9"*) install_CStm_RHEL_OL_pre_reqs $1 python36-pip python3.6;
                ;;
        "Red Hat Enterprise Linux"*) op_st_os_distro=$(cat /etc/*release | tail -n 1);
                 if [[ "$op_st_os_distro" == *"Red Hat Enterprise Linux Server release 7.9"* ]]; then install_CStm_RHEL_OL_pre_reqs $1 python36-pip python3.6;
                 else echo "Unmatched OS version detected ! Aborting pre-requisites installtion !"
                 fi
                ;;
        "Oracle Linux Server 8.8"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
                ;;
        "Oracle Linux Server 8.10"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
                ;;
        "Ubuntu 20.04"*) install_Ub20_pre_reqs $1;
                ;;
        "CentOS Linux 8 (Core)") echo "installation currently not supported due to unknow mirror repo-configuration. Aborting! ";
                #install_CStm_RHEL_OL_pre_reqs $1 python39-pip python3.9;
                ;;
        *) echo "Unmatched OS version detected ! Aborting pre-requisites installtion !"
                ;;
esac
echo "------OS distro detected: $os_distro-------------"
#echo $py_arr  #only when return required
}

#----------------------------------- Function to apply NTP synchronization--------------------------#
apply_NTP_sync() {

echo " -------- Checking NTP sync ----------"
# Check if Chrony is installed
if ! command -v chronyd &>/dev/null; then
  echo "---------- Chrony is not installed - installing & activating ----------."
  sudo yum install -y chrony
  sudo systemctl start chronyd &&  sudo systemctl enable chronyd
  sudo timedatectl set-ntp true
  echo "---- NTP by chrony installed & activated. Request admin to edit /etc/chrony.conf with relevant NTP server/pools in all vms ---"
fi

# Check if Chrony service is enabled
if ! systemctl is-enabled --quiet chronyd; then
  echo "Chrony service is not enabled. Enabling..."
  sudo systemctl enable chronyd
fi

# Check if Chrony service is running
if systemctl is-active --quiet chronyd; then
  echo "Chrony is installed and running."
else
  echo "---------- Chrony is installed but not running. Activating ... ----------"
  sudo systemctl start chronyd && sudo systemctl enable chronyd
  echo "---- NTP by chrony activated. Request admin to edit /etc/chrony.conf with relevant NTP server/pools in all vms ---"
fi
echo " -------- end of check for NTP sync ----------"
}

#Function for ################# CentOS/RHEL/7.9/8.6/8.8/8.10/9.4/CentOSStream8/OracleLinux8.8 ###############

install_CStm_RHEL_OL_pre_reqs() {

arg=$(echo $1 | tr '[:upper:]' '[:lower:]')
if [ "$#" -eq 3 ] && [ -n "$arg" ] && ( [ "$arg" = "master" ] || [ "$arg" = "worker" ] ); then
  echo "Executing for request: $arg"
  if [ "$arg" = "master" ]; then

        sudo yum install $2 -y
        sudo pip3 install --upgrade pip
        /usr/bin/$3  -m venv py3
        PWD=`pwd`
        source "$PWD/py3/bin/activate"

        echo "--------------------virtual environment activated--------------------------"
        pip install --upgrade pip
        pip install wheel
        pip install  ansible-core==2.17
        ansible-galaxy collection install ansible.posix
        ansible-galaxy collection install containers.podman

        echo "--------------------Starting other library installation in $arg -------------------"
	sudo yum install fio-3.19 -y
        sudo yum  install -y  podman sshpass nfs-utils git vim bzip2 tree iptables
        sudo yum --setopt=tsflags=noscripts install iscsi-initiator-utils -y
        sudo systemctl enable iscsid
        sudo systemctl start iscsid

        #echo "--------------------Pre-requisites installation complete in $arg ! -------------------"
  fi

  if [ "$arg" = "worker" ]; then

        echo "--------------------Starting library installation in $arg -------------------"
	sudo yum install $2 -y
        sudo pip3 install --upgrade pip
	sudo yum install fio-3.19 -y
        sudo yum  install -y sshpass nfs-utils vim bzip2 tar tree iptables
        sudo yum --setopt=tsflags=noscripts install iscsi-initiator-utils -y
        sudo systemctl enable iscsid
        sudo systemctl start iscsid
       #echo "--------------------Pre-requisites installation complete in $arg ! -------------------"
  fi

  # Call the apply_ntp_sync function
  [ "$ntp_check" = true ] && apply_NTP_sync || echo " ----skipping NTP check based on condition-----"

  else if ( [ "$arg" != "master" ]  || [ "$arg" != "worker" ] ); then
        echo "Empty/incorrect arguments: ,please specify either master or worker!. Optionally append 'ntp' if check required"
	echo  "=> Usage(1): sh pre-req-installer.sh master"
	echo  "=> Usage(2): sh pre-req-installer.sh master ntp"
  fi
fi
}

#Function for ################# Ubuntu 20.04 ###############
#ntp check not supported
install_Ub20_pre_reqs() {
arg=$(echo $1 | tr '[:upper:]' '[:lower:]')
if [ "$#" -eq 1 ] && [ -n "$arg" ] && ( [ "$arg" = "master" ] || [ "$arg" = "worker" ] ); then
  # Your commands here
  echo "Executing for request: $arg"
  if [ "$arg" = "master" ]; then

        sudo apt-get update -y
        sudo apt-get install python3-pip  -y
        sudo apt-get install python3-venv -y
        python3 -m venv py3
        PWD=`pwd`
        source "$PWD/py3/bin/activate"

        echo "--------------------virtual environment activated--------------------------"
        pip install --upgrade pip
        pip install wheel
        pip install  ansible==2.9.27
        ansible-galaxy collection install containers.podman
        export PATH=$PATH:/usr/local/bin

        echo "--------------------Starting other library installation in $arg -------------------"
        source /etc/os-release
        echo "deb https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /" | sudo tee /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list
        curl -L https://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/Release.key | sudo apt-key add -
        sudo apt-get -y update
	sudo apt-get install fio-3.7 -y
        sudo apt-get -y install  podman sshpass nfs-kernel-server git vim open-iscsi bzip2 tree
        sudo systemctl enable iscsid
        sudo systemctl start iscsid
        echo "--------------------Pre-requisites installation complete in $arg ! -------------------"
  fi

  if [ "$arg" = "worker" ]; then

        echo "--------------------Starting library installation in $arg -------------------"
        sudo apt-get -y update
	sudo apt-get install python3-pip  -y
	sudo apt-get install fio-3.7 -y
        sudo apt-get -y install sshpass nfs-common open-iscsi vim bzip2 tree
        sudo systemctl enable iscsid
        sudo systemctl start iscsid
        echo "--------------------Pre-requisites installation complete in $arg ! -------------------"
  fi

else
  echo "Empty/incorrect arguments: $arg ,please specify either master or worker!"
  echo  "=> Usage: sh pre-req-installer.sh master"
fi
}

#Execution starts here  #################### with 'master' or 'worker' argument from CLI########################
check_os_distribution $1
