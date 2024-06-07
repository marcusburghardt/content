#!/usr/bin/python3

import argparse
import os
import re
import glob
from collections import defaultdict

try:
    from utils.controleval import (
        get_available_products,
        get_product_profiles_files,
        load_controls_manager,
    )
    from utils.profile_tool.profile import get_profile
    from ssg.rules import find_rule_dirs_in_paths
    from ssg.products import Product, product_yaml_path, _get_implied_properties
    from ssg.jinja import update_substitutions_dict, _get_jinja_environment
    from ssg.yaml import open_and_macro_expand
except ImportError:
    print("The ssg module could not be found.")
    print(
        "Run .pyenv.sh available in the project root directory,"
        " or add it to PYTHONPATH manually."
    )
    print("$ source .pyenv.sh")
    exit(1)


def _get_root_dir() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.join(current_dir, '..')
    return os.path.normpath(project_root_dir)


def _load_controls_manager(product: str):
    root_dir = _get_root_dir()
    controls_dir = os.path.join(root_dir, 'controls')
    return load_controls_manager(controls_dir, product)


def _get_profiles_from_product(products: list) -> list:
    profiles = []
    for product in products:
        controls_manager = _load_controls_manager(product)
        profiles_files = get_product_profiles_files(product)
        for file in profiles_files:
            profiles.append(get_profile(profiles_files, file, controls_manager.policies))
    return profiles


def _get_rules_from_profiles(profiles: list) -> list:
    rules_set = set()
    for profile in profiles:
        rules_set.update(profile.rules)
    return sorted(rules_set)


def _convert_defaultdict_to_dict(dictionary: defaultdict) -> dict:
    if isinstance(dictionary, defaultdict):
        dictionary = {k: _convert_defaultdict_to_dict(v) for k, v in dictionary.items()}
    return dictionary


def _get_variables_from_profiles(profiles: list) -> dict:
    variables = defaultdict(lambda: defaultdict(dict))
    for profile in profiles:
        for variable, value in profile.variables.items():
            variables[variable][profile.product][profile.id] = value
    return _convert_defaultdict_to_dict(variables)


# Locate checks
def _get_rules_base_dir(folder_within_project: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    rules_base_dir = os.path.join(current_dir, '..', folder_within_project)
    return os.path.normpath(rules_base_dir)


def _get_all_rules_dirs() -> list:
    rules_base_dirs = []
    rules_base_dirs.append(_get_rules_base_dir('linux_os/guide'))
    return list(find_rule_dirs_in_paths(rules_base_dirs))


def _has_checks_subfolder(rule_dir: str) -> bool:
    checks_dir = os.path.join(rule_dir, 'checks')
    return os.path.isdir(checks_dir)


def _has_ansible_check(rule_dir: str, ansible_file: str) -> bool:
    ansible_checks_file = os.path.join(rule_dir, ansible_file)
    return os.path.exists(ansible_checks_file)


def _get_rules_dirs_with_checks() -> list:
    all_rules_dirs = _get_all_rules_dirs()
    rules_dirs_with_checks = []
    for rule_dir in all_rules_dirs:
        if _has_checks_subfolder(rule_dir):
            rules_dirs_with_checks.append(rule_dir)
    return rules_dirs_with_checks


def _get_all_ansible_checks() -> dict:
    rules_dirs_with_checks = _get_rules_dirs_with_checks()
    ansible_file = 'checks/ansible/shared.yml'
    rules_with_ansible_check = {}

    for rule_dir in rules_dirs_with_checks:
        if _has_ansible_check(rule_dir, ansible_file):
            rule_id = os.path.basename(rule_dir)
            rules_with_ansible_check[rule_id] = os.path.join(rule_dir, ansible_file)

    return rules_with_ansible_check


def _get_selected_ansible_checks(selected_rules: list) -> dict:
    all_ansible_checks = _get_all_ansible_checks()
    selected_ansible_checks = {}

    for rule_id in all_ansible_checks:
        if rule_id in selected_rules:
            selected_ansible_checks[rule_id] = all_ansible_checks[rule_id]

    return selected_ansible_checks


def _get_all_var_files() -> list:
    base_dir = _get_rules_base_dir('linux_os/guide')
    pattern = os.path.join(base_dir, '**', '*.var')
    return glob.glob(pattern, recursive=True)


# Include test to avoid vars without default value.
def _get_variables_options() -> dict:
    all_var_files = _get_all_var_files()
    all_options = {}

    for var_file in all_var_files:
        var_id = os.path.basename(var_file).split('.var')[0]
        yaml_content = open_and_macro_expand(var_file)
        options = yaml_content.get('options', {})
        all_options[var_id] = options

    return all_options


def _get_ansible_check_macros_file() -> str:
    root_dir = _get_root_dir()
    return os.path.join(root_dir, 'shared', 'macros', '10-ansible-check.jinja')


def _find_macro_in_file(file_path: str, pattern: str) -> list:
    macro_pattern = re.compile(pattern)
    with open(file_path, 'r') as file:
        content = file.read()
        return macro_pattern.findall(content)


def _get_values_from_special_macros(selected_checks: list) -> list:
    used_variables = []
    used_properties = []
    variables_pattern = r'\{\{\{\s*ansible_check_variable\(([^)]+)\)\s*\}\}\}'
    properties_pattern = r'\{\{\{\s*ansible_check_property\(([^)]+)\)\s*\}\}\}'

    for check_id in selected_checks:
        used_variables.extend(_find_macro_in_file(selected_checks[check_id], variables_pattern))
        used_properties.extend(_find_macro_in_file(selected_checks[check_id], properties_pattern))

    return used_variables, used_properties


def _get_used_variables_and_values(used_variables: list, selected_variables: dict, profiles: list) -> dict:
    variables_options = _get_variables_options()
    variables_values = defaultdict(lambda: defaultdict(dict))

    for variable in used_variables:
        # The default value is ensured for all used variables and the exceptions are collected.
        default_value = variables_options[variable]['default']
        variables_values[variable]['default'] = default_value
        for profile in profiles:
            product_vars = selected_variables.get(variable, {})
            profile_vars = product_vars.get(profile.product, {})
            option = profile_vars.get(profile.id)
            if option is not None:
                value = variables_options[variable].get(option, default_value)
                if value != default_value:
                    variables_values[variable][profile.product][profile.id] = value

    return _convert_defaultdict_to_dict(variables_values)


def _get_used_properties_and_values(used_properties: list, profiles: list) -> dict:
    properties_defaults = _get_implied_properties(dict())
    properties_values = defaultdict(lambda: defaultdict(dict))
    root_dir = _get_root_dir()

    for property in used_properties:
        default_value = properties_defaults[property]
        for profile in profiles:
            product_vars = properties_values.get(property, {})
            value = product_vars.get(profile.product, None)
            if value is None:
                product_yaml = product_yaml_path(root_dir, profile.product)
                product = Product(product_yaml)
                product_properties = product._data_as_dict
                value = product_properties.get(property, default_value)
                if value != default_value:
                    properties_values[property][profile.product] = value
        properties_values[property]['default'] = default_value

    return _convert_defaultdict_to_dict(properties_values)


def _create_jinja_dictionary(selected_checks: list, profiles: list) -> dict:
    jinja_check_dictionary = dict()
    ansible_check_macros = _get_ansible_check_macros_file()
    selected_variables = _get_variables_from_profiles(profiles)
    used_variables, used_properties = _get_values_from_special_macros(selected_checks)
    variables_values = _get_used_variables_and_values(used_variables, selected_variables, profiles)
    properties_values = _get_used_properties_and_values(used_properties, profiles)

    update_substitutions_dict(ansible_check_macros, jinja_check_dictionary)
    jinja_check_dictionary.update(variables_values)
    jinja_check_dictionary.update(properties_values)

    return jinja_check_dictionary


def _get_rule_yml_file_from_check(check_path: str) -> str:
    parts = check_path.split(os.sep)
    modified_parts = parts[:-3]
    modified_parts.append('rule.yml')
    return os.sep.join(modified_parts)


def _get_rule_properties(check_path: str) -> dict:
    rule_yml_file = _get_rule_yml_file_from_check(check_path)
    return open_and_macro_expand(rule_yml_file)


def _append_rule_properties(check_id: str, check_path: str, jinja_check_dictionary: dict) -> dict:
    rule_properties = _get_rule_properties(check_path)
    jinja_check_dictionary['rule_id'] = check_id
    jinja_check_dictionary['rule_title'] = rule_properties['title']
    return jinja_check_dictionary


def _save_ansible_check_file(check_id: str, content: str, dest_dir: str) -> None:
    check_dest_path = os.path.join(dest_dir, f'{check_id}.yml')
    with open(check_dest_path, 'w') as check_file:
        check_file.write(content)


def _generate_ansible_checks(selected_ansible_checks, jinja_check_dictionary, output_dir=None) -> None:
    jinja_env = _get_jinja_environment(jinja_check_dictionary)

    for check_id in selected_ansible_checks:
        ansible_check_path = selected_ansible_checks[check_id]
        jinja_check_dictionary = _append_rule_properties(check_id, ansible_check_path, jinja_check_dictionary)

        ansible_check_template = jinja_env.get_template(ansible_check_path)
        rendered_playbook = ansible_check_template.render(jinja_check_dictionary)

        if output_dir:
            _save_ansible_check_file(check_id, rendered_playbook, output_dir)
        else:
            print(rendered_playbook)


def build_ansible_checks(args: argparse):
    profiles = _get_profiles_from_product(args.products)
    selected_rules = _get_rules_from_profiles(profiles)
    selected_ansible_checks = _get_selected_ansible_checks(selected_rules)
    jinja_check_dictionary = _create_jinja_dictionary(selected_ansible_checks, profiles)

    _generate_ansible_checks(selected_ansible_checks, jinja_check_dictionary, args.output_dir)


def parse_ansible_checks_subcommand(subparsers):
    parser_ansible_checks = subparsers.add_parser(
        "ansible-checks",
        description=("Generates Playbook to check rules."),
        help="Generates Playbooks for all rules with Ansible Check.",
    )
    parser_ansible_checks.add_argument(
        "--products",
        help="List of products to be considered. If not specified, apply for all products.",
        nargs="+",
        choices=get_available_products(),
        default=get_available_products(),
    )
    parser_ansible_checks.add_argument(
        "--output-dir",
        help=(
            "Directory where the Ansible Checks Playbooks will be saved. "
            "If not specified, the Playbooks will be shown in stdout.")
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Build Checks for products")
    subparsers = parser.add_subparsers(title="subcommands", dest="subcommand", required=True)
    parse_ansible_checks_subcommand(subparsers)
    args = parser.parse_args()
    return args


SUBCMDS = {
    "ansible-checks": build_ansible_checks,
}


def main():
    args = parse_args()
    SUBCMDS[args.subcommand](args)


if __name__ == "__main__":
    main()
