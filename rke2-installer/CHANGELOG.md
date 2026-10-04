# Changelog

### [v1.0] (in development)

feature/depricate_registry
- FCPSW-116, FCP-161 code commented to avoid using depricated inventory variable ext_docker_registry
- FCPSW-116, FCP-161 reverted to previous version as the ha_rke2 can be referred using inventory varaible itself
- FCPSW-116, FCP-161 resolving docker-registry-entry cleanup in hosts entry of  during delete-node of master and worker
- FCPSW-116, FCP-161 ha_rke2 explicit boolean check needed to satisfy when condition
- FCPSW-116, FCP-161 depricated registry ext_docker_registry  based on team discussion
- FCPSW-116, FCP-161 adjusting add-node plays by moving before launch_server & launch_agent nodes to remove rke2-service restarts
- FCPSW-116, FCP-161 optimizing add-node plays by moving before launch_server & launch_agent nodes to remove rke2-service restarts
- FCPSW-116, FCP-161 depricating deploy_registry.yaml play
- FCPSW-116, FCP-161 add master and worker nodes verified with busybox daemonset deployments for correct image hosting
- FCPSW-116, FCP-161 registry for add-new-agent nodes satisfied for hosts entry and ca-cert update-ca-trust
- FCPSW-116, FCP-161 Removing code for registry & rebased for conflict resolution

feature/Optimize-rke2-installer
- updated choose_deploy.yaml and rke2-pod-status yaml
- Removed hardcodes while clearing /etc/hosts
- Updated images cleanup to run only on master nodes
- Revert "Removed rancher environment dependencies from parent plays"
- Updated launch agent node play with ansible user home path
- Removed rancher environment dependencies from parent plays
- Removed minimal hardcode timings
- Corrected vip main.yaml
- updated DDOS patch role
- Pulled DDOS-Patch from CICAD-Dev/7.5
- Removed delete_pending_pods play
- upgrading kube-vip image from v0.8.0 to v1.0.3
- updated main.yaml as per dev/7.5
- Deprecated /tmp usage

feature/rke2v.1.34.1
- remove_dns missed cleaning registry_entry. fixed
- Initial rke2-install changes
- dev/7.5 minimum files selectively cherrypicked  FCPSW-91 FCP-134
- uninstall correction cheerryrpicked from dev/7.5
- FCPSW-91 RKE2 v1.34.1 feature upgrade

feature/swap_config
- FCPSW-121, FCP-149 Updated tags for kubelet and swap configurations. Updated roles for proper swap enable and disable configurations
