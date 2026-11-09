#!/bin/sh

#Note:
#(i) Skip the pre-requisite-installer.sh script if RKE2 was installed using 1fcp-community.
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
##############################################################################################################################

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
        "Red Hat Enterprise Linux 8.10"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
                ;;
        "Red Hat Enterprise Linux 9.6"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
		;;
	"Oracle Linux Server 8.10"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
                ;;
        "Oracle Linux Server 9.6"*) install_CStm_RHEL_OL_pre_reqs $1 python3.12-pip python3.12;
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

#Function for ################# OracleLinux/RHEL/8.10/9.6 ###############

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

#Execution starts here  #################### with 'master' or 'worker' argument from CLI########################
check_os_distribution $1
