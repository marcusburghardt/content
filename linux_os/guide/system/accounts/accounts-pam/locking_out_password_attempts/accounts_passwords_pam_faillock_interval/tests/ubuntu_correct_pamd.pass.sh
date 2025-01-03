#!/bin/bash
# platform = multi_platform_ubuntu
# variables = var_accounts_passwords_pam_faillock_fail_interval=800

cat << EOF > /usr/share/pam-configs/faillock
Name: Enable pam_faillock to deny access
Default: yes
Priority: 0
Auth-Type: Primary
Auth:
    [default=die]                   pam_faillock.so authfail fail_interval=900
EOF

cat << EOF > /usr/share/pam-configs/faillock_notify
Name: Notify of failed login attempts and reset count upon success
Default: yes
Priority: 1024
Auth-Type: Primary
Auth:
    requisite                       pam_faillock.so preauth fail_interval=900
Account-Type: Primary
Account:
    required                        pam_faillock.so
EOF

DEBIAN_FRONTEND=noninteractive pam-auth-update
