# platform = Red Hat Virtualization 4,multi_platform_fedora,multi_platform_ol,multi_platform_rhel,multi_platform_sle,multi_platform_slmicro,multi_platform_ubuntu,multi_platform_debian,multi_platform_almalinux

# Perform the remediation for both possible tools: 'auditctl' and 'augenrules'
{{{ bash_fix_audit_watch_rule("auditctl", "/etc/localtime", "wa", "audit_time_rules") }}}
{{{ bash_fix_audit_watch_rule("augenrules", "/etc/localtime", "wa", "audit_time_rules") }}}
