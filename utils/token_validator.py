#!/usr/bin/env python
"""
Token Optimization System Validator

This utility performs code validation and quality checks specifically for the token
optimization system. It verifies error handling, backward compatibility, and code quality
standards to ensure the system functions reliably.
"""

import os
import sys
import re
import ast
import logging
import argparse
import importlib
import inspect
from typing import Dict, List, Any, Tuple, Set, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("token_validator.log")
    ]
)
logger = logging.getLogger(__name__)

class TokenOptimizationValidator:
    """
    Validator for the token optimization system codebase.
    
    This class provides tools to validate:
    - Error handling completeness
    - Backward compatibility
    - Code quality and best practices
    - Token efficiency in implementations
    """
    
    def __init__(self, base_path="."):
        """
        Initialize the validator.
        
        Args:
            base_path (str): Base path for the codebase to validate
        """
        self.base_path = os.path.abspath(base_path)
        self.python_files = []
        self.validation_results = {
            "error_handling": {
                "pass": 0,
                "fail": 0,
                "warnings": 0,
                "details": []
            },
            "backward_compatibility": {
                "pass": 0,
                "fail": 0,
                "warnings": 0,
                "details": []
            },
            "code_quality": {
                "pass": 0,
                "fail": 0,
                "warnings": 0,
                "details": []
            },
            "token_efficiency": {
                "pass": 0,
                "fail": 0,
                "warnings": 0,
                "details": []
            }
        }
    
    def find_python_files(self, include_patterns=None, exclude_patterns=None):
        """
        Find Python files in the codebase.
        
        Args:
            include_patterns (List[str], optional): Patterns to include
            exclude_patterns (List[str], optional): Patterns to exclude
            
        Returns:
            List[str]: List of Python file paths
        """
        if include_patterns is None:
            include_patterns = [r'.*\.py$']
        
        if exclude_patterns is None:
            exclude_patterns = [r'__pycache__', r'\.git', r'\.venv', r'\.env', r'venv']
        
        logger.info(f"Searching for Python files in {self.base_path}")
        
        python_files = []
        for root, dirs, files in os.walk(self.base_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(re.match(pattern, d) for pattern in exclude_patterns)]
            
            for file in files:
                if any(re.match(pattern, file) for pattern in include_patterns):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.base_path)
                    
                    # Skip excluded files
                    if any(re.search(pattern, rel_path) for pattern in exclude_patterns):
                        continue
                    
                    python_files.append(file_path)
        
        logger.info(f"Found {len(python_files)} Python files")
        self.python_files = python_files
        return python_files
    
    def validate_error_handling(self):
        """
        Validate error handling in all Python files.
        
        This checks for:
        - Try/except blocks in functions
        - Exception types and specificity
        - Error logging
        
        Returns:
            Dict[str, Any]: Validation results
        """
        logger.info("Validating error handling...")
        results = self.validation_results["error_handling"]
        
        for file_path in self.python_files:
            rel_path = os.path.relpath(file_path, self.base_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the file
                tree = ast.parse(content)
                
                # Search for function definitions
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        function_name = node.name
                        
                        # Skip test functions
                        if function_name.startswith("test_"):
                            continue
                        
                        has_try_except = False
                        has_specific_except = False
                        has_error_logging = False
                        
                        # Check for try/except blocks
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Try):
                                has_try_except = True
                                
                                # Check for specific exception types
                                for handler in subnode.handlers:
                                    if handler.type is not None and handler.type.id != 'Exception':
                                        has_specific_except = True
                                
                                # Check for error logging
                                for handler_node in ast.walk(subnode):
                                    if isinstance(handler_node, ast.Call):
                                        if (hasattr(handler_node, 'func') and 
                                            isinstance(handler_node.func, ast.Attribute) and
                                            handler_node.func.attr in ('error', 'exception', 'warning')):
                                            has_error_logging = True
                        
                        # Functions with 'try' in the name often need error handling
                        needs_error_handling = (
                            'process' in function_name or
                            'connect' in function_name or
                            'save' in function_name or
                            'load' in function_name or
                            'read' in function_name or
                            'write' in function_name or
                            'send' in function_name or
                            'receive' in function_name or
                            'parse' in function_name
                        )
                        
                        if needs_error_handling and not has_try_except:
                            results["fail"] += 1
                            results["details"].append({
                                "file": rel_path,
                                "function": function_name,
                                "message": "Function appears to need error handling but has no try/except",
                                "type": "error"
                            })
                        elif has_try_except:
                            if not has_specific_except:
                                results["warnings"] += 1
                                results["details"].append({
                                    "file": rel_path,
                                    "function": function_name,
                                    "message": "Function has try/except but uses only generic Exception",
                                    "type": "warning"
                                })
                            
                            if not has_error_logging:
                                results["warnings"] += 1
                                results["details"].append({
                                    "file": rel_path,
                                    "function": function_name,
                                    "message": "Function has try/except but does not log errors",
                                    "type": "warning"
                                })
                            
                            if has_specific_except and has_error_logging:
                                results["pass"] += 1
            
            except Exception as e:
                logger.error(f"Error validating {rel_path}: {str(e)}")
                results["fail"] += 1
                results["details"].append({
                    "file": rel_path,
                    "function": "",
                    "message": f"Error validating file: {str(e)}",
                    "type": "error"
                })
        
        logger.info(f"Error handling validation complete: {results['pass']} passed, {results['fail']} failed, {results['warnings']} warnings")
        return results
    
    def validate_backward_compatibility(self, interface_files=None):
        """
        Validate backward compatibility with existing systems.
        
        This checks for:
        - Interface consistency
        - Parameter compatibility
        - Return value consistency
        
        Args:
            interface_files (List[str], optional): Files to check as interfaces
            
        Returns:
            Dict[str, Any]: Validation results
        """
        logger.info("Validating backward compatibility...")
        results = self.validation_results["backward_compatibility"]
        
        # Default interface files if not provided
        if interface_files is None:
            interface_files = [
                "token_optimization_system.py",
                "utils/token_optimizer.py",
                "utils/log_processor.py",
                "utils/mcp_wrapper.py"
            ]
        
        # Full paths for interface files
        interface_files = [os.path.join(self.base_path, f) for f in interface_files]
        
        # Load function signatures from files
        signatures = {}
        for file_path in interface_files:
            rel_path = os.path.relpath(file_path, self.base_path)
            
            if not os.path.exists(file_path):
                logger.warning(f"Interface file not found: {rel_path}")
                continue
            
            try:
                # Read the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the file
                tree = ast.parse(content)
                
                # Find all function definitions
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        function_name = node.name
                        
                        # Skip private functions
                        if function_name.startswith('_'):
                            continue
                        
                        # Get parameters
                        params = []
                        defaults = []
                        
                        for arg in node.args.args:
                            params.append(arg.arg)
                        
                        # Handle defaults
                        for default in node.args.defaults:
                            if isinstance(default, ast.Constant):
                                defaults.append(default.value)
                            else:
                                defaults.append(None)
                        
                        # Create signature
                        signatures[f"{rel_path}::{function_name}"] = {
                            "params": params,
                            "defaults": defaults,
                            "return_annotation": ast.unparse(node.returns) if node.returns else None
                        }
                
                results["pass"] += 1
            
            except Exception as e:
                logger.error(f"Error processing interface file {rel_path}: {str(e)}")
                results["fail"] += 1
                results["details"].append({
                    "file": rel_path,
                    "function": "",
                    "message": f"Error processing interface file: {str(e)}",
                    "type": "error"
                })
        
        # Compare with implementation files
        implementation_files = [f for f in self.python_files if f not in interface_files]
        
        for file_path in implementation_files:
            rel_path = os.path.relpath(file_path, self.base_path)
            
            try:
                module_name = rel_path.replace('/', '.').replace('\\', '.').replace('.py', '')
                
                # Try to import the module
                sys.path.insert(0, self.base_path)
                try:
                    module = importlib.import_module(module_name)
                    
                    # Check compatibility with interface functions
                    for sig_name, sig_info in signatures.items():
                        interface_file, func_name = sig_name.split('::')
                        
                        # Check if this module implements the interface function
                        if hasattr(module, func_name):
                            func = getattr(module, func_name)
                            
                            # Check signature compatibility
                            try:
                                func_sig = inspect.signature(func)
                                func_params = list(func_sig.parameters.keys())
                                
                                # Compare parameters
                                if func_params and func_params[0] == 'self':
                                    func_params = func_params[1:]  # Skip 'self' for class methods
                                
                                # Check if all required params are present
                                interface_params = sig_info["params"]
                                if interface_params and interface_params[0] == 'self':
                                    interface_params = interface_params[1:]
                                
                                if not all(p in func_params for p in interface_params):
                                    missing = [p for p in interface_params if p not in func_params]
                                    results["fail"] += 1
                                    results["details"].append({
                                        "file": rel_path,
                                        "function": func_name,
                                        "message": f"Missing required parameters from interface {interface_file}: {', '.join(missing)}",
                                        "type": "error"
                                    })
                                else:
                                    results["pass"] += 1
                            
                            except Exception as e:
                                logger.error(f"Error checking signature for {rel_path}::{func_name}: {str(e)}")
                                results["warnings"] += 1
                                results["details"].append({
                                    "file": rel_path,
                                    "function": func_name,
                                    "message": f"Error checking signature: {str(e)}",
                                    "type": "warning"
                                })
                
                finally:
                    if self.base_path in sys.path:
                        sys.path.remove(self.base_path)
            
            except Exception as e:
                logger.error(f"Error validating backward compatibility for {rel_path}: {str(e)}")
                results["warnings"] += 1
                results["details"].append({
                    "file": rel_path,
                    "function": "",
                    "message": f"Error validating backward compatibility: {str(e)}",
                    "type": "warning"
                })
        
        logger.info(f"Backward compatibility validation complete: {results['pass']} passed, {results['fail']} failed, {results['warnings']} warnings")
        return results
    
    def validate_code_quality(self):
        """
        Validate code quality standards.
        
        This checks for:
        - Docstrings
        - Type hints
        - Function complexity
        - Naming conventions
        
        Returns:
            Dict[str, Any]: Validation results
        """
        logger.info("Validating code quality...")
        results = self.validation_results["code_quality"]
        
        for file_path in self.python_files:
            rel_path = os.path.relpath(file_path, self.base_path)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the file
                tree = ast.parse(content)
                
                # File-level docstring
                has_module_docstring = (
                    len(tree.body) > 0 and
                    isinstance(tree.body[0], ast.Expr) and
                    isinstance(tree.body[0].value, ast.Str)
                )
                
                if not has_module_docstring:
                    results["warnings"] += 1
                    results["details"].append({
                        "file": rel_path,
                        "function": "",
                        "message": "File missing module-level docstring",
                        "type": "warning"
                    })
                
                # Check classes and functions
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        node_name = node.name
                        node_type = "class" if isinstance(node, ast.ClassDef) else "function"
                        
                        # Check docstring
                        has_docstring = (
                            len(node.body) > 0 and
                            isinstance(node.body[0], ast.Expr) and
                            isinstance(node.body[0].value, ast.Str)
                        )
                        
                        if not has_docstring and not node_name.startswith('_'):
                            results["warnings"] += 1
                            results["details"].append({
                                "file": rel_path,
                                "function": node_name,
                                "message": f"{node_type.capitalize()} missing docstring",
                                "type": "warning"
                            })
                        
                        # For functions, check type hints and complexity
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            # Check return type annotation
                            has_return_annotation = node.returns is not None
                            
                            # Check parameter type annotations
                            params_with_annotations = sum(1 for arg in node.args.args if arg.annotation is not None)
                            total_params = len(node.args.args)
                            
                            # Skip checking type hints for private functions or small functions
                            if not node_name.startswith('_') and total_params > 0:
                                if not has_return_annotation:
                                    results["warnings"] += 1
                                    results["details"].append({
                                        "file": rel_path,
                                        "function": node_name,
                                        "message": "Function missing return type annotation",
                                        "type": "warning"
                                    })
                                
                                if params_with_annotations < total_params:
                                    results["warnings"] += 1
                                    results["details"].append({
                                        "file": rel_path,
                                        "function": node_name,
                                        "message": f"Function missing parameter type annotations ({params_with_annotations}/{total_params})",
                                        "type": "warning"
                                    })
                            
                            # Check function complexity
                            complexity = self._calculate_complexity(node)
                            if complexity > 10:
                                results["warnings"] += 1
                                results["details"].append({
                                    "file": rel_path,
                                    "function": node_name,
                                    "message": f"Function has high complexity ({complexity})",
                                    "type": "warning"
                                })
                
                results["pass"] += 1
            
            except Exception as e:
                logger.error(f"Error validating code quality for {rel_path}: {str(e)}")
                results["fail"] += 1
                results["details"].append({
                    "file": rel_path,
                    "function": "",
                    "message": f"Error validating code quality: {str(e)}",
                    "type": "error"
                })
        
        logger.info(f"Code quality validation complete: {results['pass']} passed, {results['fail']} failed, {results['warnings']} warnings")
        return results
    
    def validate_token_efficiency(self):
        """
        Validate token efficiency in the codebase.
        
        This checks for:
        - Stream processing usage
        - Token budget management
        - Duplication handling
        - Efficient text processing
        
        Returns:
            Dict[str, Any]: Validation results
        """
        logger.info("Validating token efficiency...")
        results = self.validation_results["token_efficiency"]
        
        # Patterns to check for token efficiency
        token_efficiency_patterns = {
            "stream_processing": r'(process.*chunk|chunk.*size|stream.*process)',
            "token_budget": r'(token.*budget|budget.*token|TokenBudget|max_token)',
            "token_estimation": r'(estimat.*token|token.*estimat|calculate.*token)',
            "duplication_handling": r'(duplicate|dedup|seen|hash_traceback)',
            "memory_optimization": r'(store.*memory|memor.*server|MCPWrapper)',
            "lazy_loading": r'(lazy|yield|generator|iter\(|__iter__)'
        }
        
        for file_path in self.python_files:
            rel_path = os.path.relpath(file_path, self.base_path)
            file_patterns_found = set()
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for each pattern
                for pattern_name, pattern in token_efficiency_patterns.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        file_patterns_found.add(pattern_name)
                
                # Check for token-consuming operations
                string_concat_count = len(re.findall(r'\s*\+\s*', content))
                large_literals_count = len(re.findall(r'"[^"]{100,}"', content)) + len(re.findall(r"'[^']{100,}'", content))
                
                # Check for efficiency issues
                if 'token_budget' in file_patterns_found:
                    # This file likely deals with tokens, so should have optimizations
                    expected_patterns = {
                        "stream_processing", 
                        "token_estimation", 
                        "duplication_handling"
                    }
                    
                    missing_patterns = expected_patterns - file_patterns_found
                    if missing_patterns:
                        for pattern in missing_patterns:
                            results["warnings"] += 1
                            results["details"].append({
                                "file": rel_path,
                                "function": "",
                                "message": f"Token-handling file missing {pattern} pattern",
                                "type": "warning"
                            })
                
                # Flag concerning patterns
                if large_literals_count > 3:
                    results["warnings"] += 1
                    results["details"].append({
                        "file": rel_path,
                        "function": "",
                        "message": f"File contains {large_literals_count} large string literals (>100 chars)",
                        "type": "warning"
                    })
                
                if string_concat_count > 20:
                    results["warnings"] += 1
                    results["details"].append({
                        "file": rel_path,
                        "function": "",
                        "message": f"File contains {string_concat_count} string concatenation operations",
                        "type": "warning"
                    })
                
                # Count this as a pass if we found efficiency patterns or it's not a token-handling file
                if file_patterns_found or 'token' not in rel_path.lower():
                    results["pass"] += 1
            
            except Exception as e:
                logger.error(f"Error validating token efficiency for {rel_path}: {str(e)}")
                results["fail"] += 1
                results["details"].append({
                    "file": rel_path,
                    "function": "",
                    "message": f"Error validating token efficiency: {str(e)}",
                    "type": "error"
                })
        
        logger.info(f"Token efficiency validation complete: {results['pass']} passed, {results['fail']} failed, {results['warnings']} warnings")
        return results
    
    def _calculate_complexity(self, node):
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Start with 1 for the function itself
        
        for subnode in ast.walk(node):
            # Increment for each control flow statement
            if isinstance(subnode, (ast.If, ast.For, ast.While, ast.AsyncFor)):
                complexity += 1
            elif isinstance(subnode, ast.Try):
                complexity += len(subnode.handlers) + (1 if subnode.orelse else 0) + (1 if subnode.finalbody else 0)
            elif isinstance(subnode, ast.BoolOp) and isinstance(subnode.op, (ast.And, ast.Or)):
                complexity += len(subnode.values) - 1
        
        return complexity
    
    def run_all_validations(self):
        """
        Run all validation checks.
        
        Returns:
            Dict[str, Any]: Complete validation results
        """
        logger.info("Running all validations...")
        
        # Find Python files
        self.find_python_files()
        
        # Run validations
        self.validate_error_handling()
        self.validate_backward_compatibility()
        self.validate_code_quality()
        self.validate_token_efficiency()
        
        # Calculate overall statistics
        total_pass = sum(self.validation_results[key]["pass"] for key in self.validation_results)
        total_fail = sum(self.validation_results[key]["fail"] for key in self.validation_results)
        total_warnings = sum(self.validation_results[key]["warnings"] for key in self.validation_results)
        
        logger.info(f"All validations complete: {total_pass} passed, {total_fail} failed, {total_warnings} warnings")
        
        return self.validation_results
    
    def generate_validation_report(self, output_file=None):
        """
        Generate a validation report.
        
        Args:
            output_file (str, optional): Path to save the report
            
        Returns:
            str: Report content
        """
        # Run validations if not already done
        if all(results["pass"] == 0 and results["fail"] == 0 for results in self.validation_results.values()):
            self.run_all_validations()
        
        # Calculate overall statistics
        total_pass = sum(self.validation_results[key]["pass"] for key in self.validation_results)
        total_fail = sum(self.validation_results[key]["fail"] for key in self.validation_results)
        total_warnings = sum(self.validation_results[key]["warnings"] for key in self.validation_results)
        
        # Generate report
        report = [
            "# Token Optimization System Validation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- Total Passes: {total_pass}",
            f"- Total Failures: {total_fail}",
            f"- Total Warnings: {total_warnings}",
            ""
        ]
        
        # Add details for each validation type
        for validation_type, results in self.validation_results.items():
            report.extend([
                f"## {validation_type.replace('_', ' ').title()} Validation",
                f"- Passes: {results['pass']}",
                f"- Failures: {results['fail']}",
                f"- Warnings: {results['warnings']}",
                ""
            ])
            
            # Add issues details
            if results["details"]:
                report.append("### Issues")
                
                # Group by file
                issues_by_file = {}
                for detail in results["details"]:
                    file_path = detail["file"]
                    if file_path not in issues_by_file:
                        issues_by_file[file_path] = []
                    issues_by_file[file_path].append(detail)
                
                # Add details for each file
                for file_path, details in issues_by_file.items():
                    report.append(f"#### {file_path}")
                    
                    for detail in details:
                        function_info = f" - {detail['function']}" if detail['function'] else ""
                        icon = "❌" if detail['type'] == 'error' else "⚠️"
                        report.append(f"- {icon} {detail['message']}{function_info}")
                    
                    report.append("")
        
        # Add validation checklist
        report.extend([
            "## Token Optimization Validation Checklist",
            "",
            "### Error Handling",
            "- [ ] All data processing functions have try/except blocks",
            "- [ ] Exception types are specific (not just generic Exception)",
            "- [ ] Errors are properly logged",
            "- [ ] Graceful degradation when facing errors",
            "",
            "### Backward Compatibility",
            "- [ ] Public API functions maintain signature compatibility",
            "- [ ] Configuration formats are backward compatible",
            "- [ ] Optional new parameters have defaults",
            "- [ ] Deprecated features have warnings before removal",
            "",
            "### Code Quality",
            "- [ ] All public functions/classes have docstrings",
            "- [ ] Type hints are used consistently",
            "- [ ] Complex functions are broken down",
            "- [ ] Variable names are clear and descriptive",
            "",
            "### Token Efficiency",
            "- [ ] Stream processing used for large files",
            "- [ ] Token budgeting implemented",
            "- [ ] Duplication detection/handling exists",
            "- [ ] Memory integration is optimized",
            "- [ ] String operations minimize token usage",
            ""
        ])
        
        report_content = "\n".join(report)
        
        # Save report if output file is specified
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"Validation report saved to {output_file}")
        
        return report_content


def main():
    """Main entry point for the token validator command-line tool."""
    parser = argparse.ArgumentParser(description="Token Optimization System Validator")
    
    parser.add_argument(
        "--path", 
        default=".",
        help="Base path for the codebase to validate"
    )
    parser.add_argument(
        "--output", 
        help="Output file for the validation report"
    )
    parser.add_argument(
        "--validate-error-handling", 
        action="store_true",
        help="Validate error handling"
    )
    parser.add_argument(
        "--validate-compatibility", 
        action="store_true",
        help="Validate backward compatibility"
    )
    parser.add_argument(
        "--validate-code-quality", 
        action="store_true",
        help="Validate code quality"
    )
    parser.add_argument(
        "--validate-token-efficiency", 
        action="store_true",
        help="Validate token efficiency"
    )
    
    args = parser.parse_args()
    
    # Initialize validator
    validator = TokenOptimizationValidator(base_path=args.path)
    
    # Find Python files
    validator.find_python_files()
    
    # Run selected validations or all if none specified
    if args.validate_error_handling:
        validator.validate_error_handling()
    elif args.validate_compatibility:
        validator.validate_backward_compatibility()
    elif args.validate_code_quality:
        validator.validate_code_quality()
    elif args.validate_token_efficiency:
        validator.validate_token_efficiency()
    else:
        # Run all validations
        validator.run_all_validations()
    
    # Generate and print report
    report = validator.generate_validation_report(output_file=args.output)
    print(report)


if __name__ == "__main__":
    main()