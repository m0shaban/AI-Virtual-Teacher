#!/usr/bin/env python3
"""
Deployment script for Hugging Face Spaces
"""

import os
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd
        )
        if result.returncode != 0:
            print(f"❌ Command failed: {command}")
            print(f"Error: {result.stderr}")
            return False
        print(f"✅ Command successful: {command}")
        if result.stdout:
            print(result.stdout)
        return True
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def setup_space_repository():
    """Setup the Hugging Face Space repository."""
    print("🚀 Setting up Hugging Face Space repository...")
    
    # Create a temporary directory for the space
    space_dir = Path("huggingface_space")
    if space_dir.exists():
        shutil.rmtree(space_dir)
    space_dir.mkdir()
    
    print(f"📁 Created directory: {space_dir}")
    
    # Initialize git repository
    if not run_command("git init", cwd=space_dir):
        return False
    
    # Set up git remote (replace with your actual space URL)
    space_url = "https://huggingface.co/spaces/moshabann/Virtual_Teachers"
    if not run_command(f"git remote add origin {space_url}", cwd=space_dir):
        return False
    
    return space_dir

def copy_files_to_space(space_dir):
    """Copy necessary files to the space directory."""
    print("📋 Copying files to space directory...")
    
    files_to_copy = [
        ("app.py", "app.py"),
        ("requirements.txt", "requirements.txt"),
        ("README_SPACE.md", "README.md"),
        (".gitignore_space", ".gitignore")
    ]
    
    for src, dst in files_to_copy:
        src_path = Path(src)
        dst_path = space_dir / dst
        
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"✅ Copied {src} -> {dst}")
        else:
            print(f"⚠️ File not found: {src}")
    
    return True

def deploy_to_space(space_dir):
    """Deploy the application to Hugging Face Spaces."""
    print("🚀 Deploying to Hugging Face Spaces...")
    
    # Add all files
    if not run_command("git add .", cwd=space_dir):
        return False
    
    # Commit changes
    commit_message = "Deploy AI Virtual Teacher - Multi-model educational assistant"
    if not run_command(f'git commit -m "{commit_message}"', cwd=space_dir):
        return False
    
    # Push to Hugging Face
    print("📤 Pushing to Hugging Face Spaces...")
    print("⚠️ You will be prompted for your Hugging Face username and token.")
    print("💡 Use your Hugging Face access token as the password.")
    
    if not run_command("git push -u origin main", cwd=space_dir):
        return False
    
    return True

def main():
    """Main deployment function."""
    print("🎓 AI Virtual Teacher - Hugging Face Spaces Deployment")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ app.py not found. Please run this script from the project directory.")
        return False
    
    # Setup space repository
    space_dir = setup_space_repository()
    if not space_dir:
        return False
    
    # Copy files
    if not copy_files_to_space(space_dir):
        return False
    
    # Deploy
    if not deploy_to_space(space_dir):
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Deployment completed successfully!")
    print("🔗 Your space should be available at:")
    print("   https://huggingface.co/spaces/moshabann/Virtual_Teachers")
    print("\n💡 Tips:")
    print("   - It may take a few minutes for the space to build")
    print("   - Check the logs if there are any issues")
    print("   - Make sure to set HF_TOKEN in the space settings")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Deployment failed. Please check the errors above.")
        exit(1)
    else:
        print("\n✅ Deployment successful!")
        exit(0)
