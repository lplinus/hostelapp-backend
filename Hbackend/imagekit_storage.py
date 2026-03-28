import os
from io import BytesIO
from PIL import Image
from django.core.files.storage import Storage
from django.conf import settings
from imagekitio import ImageKit
from django.core.files.base import ContentFile

class ImageKitStorage(Storage):
    def __init__(self):
        # imagekitio 5.x initialization (Stainless based)
        # It only requires private_key. public_key and url_endpoint are not used in the constructor.
        self.client = ImageKit(
            private_key=settings.IMAGEKIT_PRIVATE_KEY,
        )

    def _save(self, name, content):
        # Normalize path
        name = name.replace('\\', '/')
        
        # Determine if it's an image that needs conversion
        ext = os.path.splitext(name)[1].lower()
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.jfif', '.avif']
        
        if ext in image_extensions:
            try:
                # Open image and convert to WebP
                img = Image.open(content)
                
                # Convert to RGB if needed
                if img.mode in ("RGBA", "LA"):
                    pass
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                    
                buffer = BytesIO()
                img.save(buffer, format="WEBP", quality=80)
                buffer.seek(0)
                
                # Update content and name
                content = ContentFile(buffer.read())
                name = os.path.splitext(name)[0] + ".webp"
            except Exception as e:
                # If conversion fails, proceed with original
                print(f"DEBUG: Storage conversion failed: {e}")
                if hasattr(content, 'seek'):
                    content.seek(0)

        folder = os.path.dirname(name)
        filename = os.path.basename(name)
        
        # Ensure we are at the start of the file
        content.seek(0)
        
        # Upload to ImageKit
        res = self.client.files.upload(
            file=content.read(),
            file_name=filename,
            folder=folder if folder else "/",
            use_unique_file_name=True,
        )
        
        if hasattr(res, 'url'):
            return res.url
            
        return name

    def url(self, name):
        # If name is already a full URL, return it
        if name.startswith('http'):
            return name
        # Otherwise, prepend endpoint
        return f"{settings.IMAGEKIT_URL_ENDPOINT.rstrip('/')}/{name.lstrip('/')}"

    def exists(self, name):
        return False

    def get_available_name(self, name, max_length=None):
        return name

    def size(self, name):
        """
        Return the size of the file in bytes.
        Since we are using ImageKit, fetching this exactly would require an API call.
        Returning 0 for now to avoid NotImplementedError in Django Admin.
        In validate_image_size, it checks the uploaded file size before it's saved.
        """
        return 0

    def delete(self, name):
        """
        Delete from ImageKit using the name/URL.
        """
        if not name:
            return

        try:
            # Extract path from URL if necessary
            path_val = name
            endpoint = settings.IMAGEKIT_URL_ENDPOINT.rstrip('/')
            if name.startswith('http'):
                if name.startswith(endpoint):
                    path_val = name[len(endpoint):].lstrip('/')
                else:
                    return

            # For SDK 5.x (Stainless), it's best to split path into folder and name
            folder = os.path.dirname(path_val)
            if not folder.startswith('/'):
                folder = '/' + folder
            filename = os.path.basename(path_val)

            # Search for the file to get its file_id
            # Using keyword arguments as per SDK 5.x
            files = self.client.files.list(name=filename, path=folder)
            
            # Since files is a ListResponse, we iterate or access [0]
            # Stainless returns a Paginator/List object
            for file in files:
                if (file.name == filename and 
                    (file.folder_path == folder or file.folder_path == folder.rstrip('/'))):
                    self.client.files.delete(file.file_id)
                    print(f"DEBUG: Deleted file {path_val} (ID: {file.file_id}) from ImageKit")
                    return # Exit after deleting first match
        except Exception as e:
            print(f"DEBUG: ImageKit delete failed for {name}: {e}")
