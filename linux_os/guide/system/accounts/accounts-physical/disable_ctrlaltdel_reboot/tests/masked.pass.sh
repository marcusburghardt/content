#!/bin/bash
# platform = Oracle Linux 7,Oracle Linux 8,multi_platform_rhel,multi_platform_fedora,multi_platform_ubuntu

systemctl disable --now ctrl-alt-del.target
systemctl mask --now ctrl-alt-del.target
