#!/bin/bash
# packages = usbguard

mkdir -p /etc/usbguard
cat << EOF > /etc/usbguard/usbguard-daemon.conf
# No AuditBackend
# in usbguard-daemon.conf
EOF
