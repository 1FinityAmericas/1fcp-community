"""
Podman client wrapper for container image operations.
Provides functionality to load, tag, push, and manage container images using Podman.
"""
import subprocess
import re
from typing import Optional, List, Dict
from src.libs.common.logger import Logger


class PodmanClientError(Exception):
    """Custom exception for Podman client errors."""
    pass


class PodmanClient:
    """
    Podman client for container image operations.
    Handles loading images from tar files, tagging, and pushing to registries.
    """
    
    def __init__(self):
        """Initialize Podman client."""
        self.logger = Logger()
        self._verify_podman_installed()
    
    def _verify_podman_installed(self):
        """
        Verify that Podman is installed and accessible.
        
        :raises PodmanClientError: If Podman is not installed or not accessible
        """
        try:
            result = subprocess.run(
                ['podman', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Podman version: {result.stdout.strip()}")
        except FileNotFoundError:
            error_msg = "Podman is not installed or not in PATH"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to verify Podman installation: {e}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
    
    def load_image(self, tar_path: str) -> str:
        """
        Load a container image from a tar file into Podman.
        
        :param tar_path: Path to the tar file containing the image
        :return: Name of the loaded image
        :raises PodmanClientError: If loading fails
        """
        try:
            self.logger.info(f"Loading image from {tar_path}")
            result = subprocess.run(
                ['podman', 'load', '-i', tar_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output to get image name
            # Expected format: "Loaded image: docker.io/library/nginx:latest"
            output = result.stdout.strip()
            self.logger.info(f"Load output: {output}")
            
            # Extract image name from output
            match = re.search(r'Loaded image[s]?:\s*(.+)', output)
            if match:
                image_name = match.group(1).strip()
                self.logger.info(f"Successfully loaded image: {image_name}")
                return image_name
            else:
                self.logger.warning(f"Could not parse image name from output: {output}")
                return output
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to load image from {tar_path}: {e.stderr}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error loading image: {e}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
    
    def tag_image(self, source_image: str, target_image: str):
        """
        Tag an image with a new name/tag.
        
        :param source_image: Source image name (e.g., nginx:latest)
        :param target_image: Target image name with registry (e.g., registry.local/nginx:1.0)
        :raises PodmanClientError: If tagging fails
        """
        try:
            self.logger.info(f"Tagging image {source_image} as {target_image}")
            subprocess.run(
                ['podman', 'tag', source_image, target_image],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully tagged image: {target_image}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to tag image {source_image} as {target_image}: {e.stderr}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
    
    def push_image(self, image_name: str, tls_verify: bool = True):
        """
        Push an image to a container registry.
        
        :param image_name: Full image name including registry (e.g., registry.local/nginx:1.0)
        :param tls_verify: Whether to verify TLS certificates (default: True)
        :raises PodmanClientError: If push fails
        """
        try:
            self.logger.info(f"Pushing image {image_name} to registry")
            cmd = ['podman', 'push']
            if not tls_verify:
                cmd.append('--tls-verify=false')
            cmd.append(image_name)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully pushed image: {image_name}")
            self.logger.debug(f"Push output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to push image {image_name}: {e.stderr}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
    
    def list_images(self, filter_name: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List container images in Podman.
        
        :param filter_name: Optional filter by image name
        :return: List of image dictionaries with repository, tag, and image ID
        :raises PodmanClientError: If listing fails
        """
        try:
            cmd = ['podman', 'images', '--format', 'json']
            if filter_name:
                cmd.extend(['--filter', f'reference={filter_name}'])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            import json
            images = json.loads(result.stdout)
            self.logger.debug(f"Found {len(images)} images")
            return images
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to list images: {e.stderr}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse image list JSON: {e}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
    
    def remove_image(self, image_name: str, force: bool = False):
        """
        Remove an image from Podman.
        
        :param image_name: Image name or ID to remove
        :param force: Force removal even if image is in use
        :raises PodmanClientError: If removal fails
        """
        try:
            self.logger.info(f"Removing image {image_name}")
            cmd = ['podman', 'rmi']
            if force:
                cmd.append('--force')
            cmd.append(image_name)
            
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"Successfully removed image: {image_name}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to remove image {image_name}: {e.stderr}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
    
    def image_exists(self, image_name: str) -> bool:
        """
        Check if an image exists in Podman.
        
        :param image_name: Image name to check
        :return: True if image exists, False otherwise
        """
        try:
            result = subprocess.run(
                ['podman', 'image', 'exists', image_name],
                capture_output=True,
                text=True
            )
            exists = result.returncode == 0
            self.logger.debug(f"Image {image_name} exists: {exists}")
            return exists
        except Exception as e:
            self.logger.error(f"Error checking if image exists: {e}")
            return False
    
    def inspect_image(self, image_name: str) -> Dict:
        """
        Inspect an image and return detailed information.
        
        :param image_name: Image name or ID to inspect
        :return: Dictionary containing image details
        :raises PodmanClientError: If inspection fails
        """
        try:
            result = subprocess.run(
                ['podman', 'inspect', image_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            import json
            image_info = json.loads(result.stdout)
            if image_info:
                return image_info[0]
            else:
                raise PodmanClientError(f"No information found for image {image_name}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to inspect image {image_name}: {e.stderr}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse inspect JSON: {e}"
            self.logger.error(error_msg)
            raise PodmanClientError(error_msg)
