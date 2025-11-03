"""
Test runner script for the React-Flask application.
Runs all tests and provides a comprehensive report.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def run_command(command, cwd=None, capture_output=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=300  
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"Command timed out: {command}")
        return None
    except Exception as e:
        print(f"Error running command: {command} - {e}")
        return None

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...")
    
    python_deps = ['pytest', 'pandas', 'numpy', 'requests']
    for dep in python_deps:
        try:
            __import__(dep)
            print(f"{dep} is installed")
        except ImportError:
            print(f"{dep} is not installed")
            return False
    
    if os.path.exists('client-react/package.json'):
        result = run_command('npm list --depth=0', cwd='client-react')
        if result and result.returncode == 0:
            print("Node.js dependencies are installed")
        else:
            print("Node.js dependencies are not installed")
            return False
    
    return True

def run_python_tests():
    """Run Python backend tests."""
    print("\nRunning Python backend tests...")
    
    result = run_command('python -m pytest server-flask/test_backend.py -v', cwd='.')
    if result and result.returncode == 0:
        print("Backend tests passed")
        return True
    else:
        print("Backend tests failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return False

def run_ml_tests():
    """Run ML model tests."""
    print("\nRunning ML model tests...")
    
    result = run_command('python -m pytest test_ml_models.py -v', cwd='.')
    if result and result.returncode == 0:
        print("ML model tests passed")
        return True
    else:
        print("ML model tests failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return False

def run_react_tests():
    """Run React frontend tests."""
    print("\nRunning React frontend tests...")
    
    if not os.path.exists('client-react/package.json'):
        print("React project not found")
        return False
    
    print("Installing React dependencies...")
    install_result = run_command('npm install', cwd='client-react')
    if not install_result or install_result.returncode != 0:
        print("Failed to install React dependencies")
        return False
        
    result = run_command('npm test -- --coverage --watchAll=false', cwd='client-react')
    if result and result.returncode == 0:
        print("React tests passed")
        return True
    else:
        print("React tests failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return False

def run_integration_tests():
    """Run integration tests."""
    print("\nRunning integration tests...")
    
    result = run_command('python -m pytest test_integration.py -v', cwd='.')
    if result and result.returncode == 0:
        print("Integration tests passed")
        return True
    else:
        print("Integration tests failed")
        if result:
            print(result.stdout)
            print(result.stderr)
        return False

def run_linting():
    """Run linting checks."""
    print("\nRunning linting checks...")
    
    python_result = run_command('python -m flake8 server-flask/ --max-line-length=120', cwd='.')
    if python_result and python_result.returncode == 0:
        print("Python linting passed")
    else:
        print("Python linting failed")
        if python_result:
            print(python_result.stdout)
            print(python_result.stderr)
    
    if os.path.exists('client-react/package.json'):
        react_result = run_command('npm run lint', cwd='client-react')
        if react_result and react_result.returncode == 0:
            print("React linting passed")
        else:
            print("React linting failed")
            if react_result:
                print(react_result.stdout)
                print(react_result.stderr)

def run_security_checks():
    """Run security checks."""
    print("\nRunning security checks...")
    
    security_issues = []
    
    secret_patterns = ['password', 'secret', 'key', 'token']
    for pattern in secret_patterns:
        result = run_command(f'grep -r -i "{pattern}" server-flask/ --include="*.py"', cwd='.')
        if result and result.stdout:
            security_issues.append(f"Potential hardcoded {pattern} found")
    
    sql_patterns = ['SELECT', 'INSERT', 'UPDATE', 'DELETE']
    for pattern in sql_patterns:
        result = run_command(f'grep -r -i "{pattern}" server-flask/ --include="*.py"', cwd='.')
        if result and result.stdout:
            security_issues.append(f"Potential SQL query found: {pattern}")
    
    if security_issues:
        print("Security issues found:")
        for issue in security_issues:
            print(f"  - {issue}")
    else:
        print("No obvious security issues found")

def generate_report(results):
    """Generate a test report."""
    print("\n" + "="*50)
    print("TEST REPORT")
    print("="*50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    failed_tests = total_tests - passed_tests
    
    print(f"Total test suites: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        print(f"  {test_name}: {status}")
    
    if failed_tests > 0:
        print("\nSome tests failed. Please check the output above for details.")
        return False
    else:
        print("\nAll tests passed!")
        return True

def main():
    """Main test runner function."""
    print("Starting comprehensive test suite...")
    print("="*50)
    
    if not os.path.exists('server-flask') or not os.path.exists('client-react'):
        print("Please run this script from the project root directory")
        sys.exit(1)
    
    if not check_dependencies():
        print("Missing dependencies. Please install them first.")
        sys.exit(1)
    
    results = {}
    
    results['Backend Tests'] = run_python_tests()
    
    results['ML Model Tests'] = run_ml_tests()

    results['React Tests'] = run_react_tests()
    
    results['Integration Tests'] = run_integration_tests()
    
    run_linting()
    
    run_security_checks()
    
    success = generate_report(results)
    
    if success:
        print("\nAll tests completed successfully!")
        sys.exit(0)
    else:
        print("\nSome tests failed. Please fix the issues and run again.")
        sys.exit(1)

if __name__ == '__main__':
    main()
