bl_info = {
    "name": "Preview Buddy",
    "author": "Bentebent",
    "version": (2, 6, 6),
    "blender": (3, 0, 0),
    "location": "3D Viewport > Sidebar > Preview Buddy",
    "description": "Quick viewport renders with per-camera frame range memory, render queue, incremental/overwrite modes and more",
    "category": "Render",
}

import bpy
import os
import re
import json
import subprocess
import platform
import time
import glob
from bpy.props import (StringProperty, EnumProperty, IntProperty, BoolProperty, 
                      CollectionProperty, PointerProperty, FloatProperty)
from bpy.types import Operator, Panel, PropertyGroup

# Define the addon category name in one place
ADDON_CATEGORY = 'Preview Buddy'

# Debug settings
DEBUG_MODE = False

# Global variable to prevent circular updates
updating = False

def debug_log(message):
    """Print debug messages if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(f"[QUICK PREVIEW DEBUG]: {message}")

def debug_camera_ranges(context):
    """Print detailed debug info about all camera ranges"""
    try:
        scene = context.scene
        debug_log("\n----- CAMERA RANGES DEBUG INFO -----")
        debug_log(f"Current camera: {scene.quickpreview_camera}")
        debug_log(f"Current frame range settings: {scene.quickpreview_frame_start} - {scene.quickpreview_frame_end}")
        debug_log(f"Scene timeline range: {scene.frame_start} - {scene.frame_end}")
        
        # Print the raw JSON data
        debug_log(f"Raw camera ranges data: {scene.quickpreview_camera_ranges}")
        
        # Parse and print the stored ranges
        try:
            data = json.loads(scene.quickpreview_camera_ranges)
            debug_log("Parsed camera ranges:")
            for camera, ranges in data.items():
                debug_log(f"  {camera}: {ranges['start']} - {ranges['end']}")
        except Exception as e:
            debug_log(f"Error parsing camera ranges: {e}")
        
        debug_log("----- END DEBUG INFO -----\n")
    except Exception as e:
        debug_log(f"Error in debug_camera_ranges: {e}")

def open_folder(path):
    """Open the folder in the file explorer"""
    try:
        directory = os.path.dirname(bpy.path.abspath(path))
        if os.path.exists(directory):
            if platform.system() == "Windows":
                os.startfile(directory)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", directory])
            else:  # Linux
                subprocess.call(["xdg-open", directory])
            debug_log(f"Opened directory: {directory}")
        else:
            debug_log(f"Directory does not exist: {directory}")
    except Exception as e:
        debug_log(f"Error opening directory: {e}")

def store_original_settings(context):
    """Store all original settings in a recoverable format"""
    scene = context.scene
    settings = {}
    
    try:
        debug_log("Backing up original render settings...")
        
        # Store core scene settings
        settings['frame_start'] = scene.frame_start
        settings['frame_end'] = scene.frame_end
        settings['camera'] = scene.camera.name if scene.camera else "None"
        
        # Store render settings
        settings['fps'] = scene.render.fps
        settings['resolution_percentage'] = scene.render.resolution_percentage
        settings['filepath'] = scene.render.filepath
        
        # Store render image settings
        settings['file_format'] = scene.render.image_settings.file_format
        settings['color_mode'] = scene.render.image_settings.color_mode
        settings['color_depth'] = scene.render.image_settings.color_depth
        if hasattr(scene.render.image_settings, 'compression'):
            settings['compression'] = scene.render.image_settings.compression
        
        # Store metadata settings
        settings['use_stamp'] = scene.render.use_stamp
        settings['use_stamp_frame'] = scene.render.use_stamp_frame
        settings['use_stamp_frame_range'] = scene.render.use_stamp_frame_range
        settings['use_stamp_camera'] = scene.render.use_stamp_camera
        settings['use_stamp_lens'] = scene.render.use_stamp_lens
        settings['use_stamp_scene'] = scene.render.use_stamp_scene
        settings['stamp_font_size'] = scene.render.stamp_font_size
        
        # Store FFMPEG settings
        settings['ffmpeg_format'] = scene.render.ffmpeg.format
        settings['ffmpeg_codec'] = scene.render.ffmpeg.codec
        settings['ffmpeg_audio_codec'] = scene.render.ffmpeg.audio_codec
        settings['ffmpeg_constant_rate_factor'] = scene.render.ffmpeg.constant_rate_factor
        settings['ffmpeg_ffmpeg_preset'] = scene.render.ffmpeg.ffmpeg_preset
        settings['ffmpeg_gopsize'] = scene.render.ffmpeg.gopsize
        settings['ffmpeg_use_autosplit'] = scene.render.ffmpeg.use_autosplit
        settings['ffmpeg_audio_channels'] = scene.render.ffmpeg.audio_channels
        settings['ffmpeg_audio_bitrate'] = scene.render.ffmpeg.audio_bitrate
        
        # Store audio settings if they exist
        if hasattr(scene.render.ffmpeg, 'audio_mixrate'):
            settings['audio_mixrate'] = scene.render.ffmpeg.audio_mixrate
        
        # Store sequencer settings if they exist
        if hasattr(scene.render, 'use_sequencer'):
            settings['use_sequencer'] = scene.render.use_sequencer
        
        # Store simplify setting
        settings['use_simplify'] = scene.render.use_simplify
        
        # Generate a unique filename based on current file
        blend_name = "unsaved"
        if bpy.data.is_saved:
            blend_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        
        # Create a timestamp for uniqueness
        import time
        timestamp = int(time.time())
        
        # Save to a temporary JSON file that can be recovered after a crash
        temp_dir = bpy.app.tempdir
        file_path = os.path.join(temp_dir, f"quickpreview_backup_{blend_name}_{timestamp}.json")
        
        with open(file_path, 'w') as f:
            json.dump(settings, f)
            
        debug_log(f"Settings backed up to {file_path}")
        return file_path, settings
        
    except Exception as e:
        debug_log(f"Failed to backup settings: {e}")
        return None, {}

def restore_original_settings(context, settings):
    """Restore original render settings from a dictionary"""
    scene = context.scene
    errors = []
    
    try:
        debug_log("Restoring original render settings...")
        

        if 'ffmpeg_constant_rate_factor' in settings:
            # Make sure we're using the correct enum values
            if isinstance(settings['ffmpeg_constant_rate_factor'], (int, str)):
                # Map the saved value to a valid enum
                if settings['ffmpeg_constant_rate_factor'] in ('15', 15):
                    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
                elif settings['ffmpeg_constant_rate_factor'] in ('23', 23):
                    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
                elif settings['ffmpeg_constant_rate_factor'] in ('28', 28):
                    scene.render.ffmpeg.constant_rate_factor = 'LOW'
                else:
                    # Default to a safe value
                    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
            else:
                # If it's already an enum value, use it directly
                scene.render.ffmpeg.constant_rate_factor = settings['ffmpeg_constant_rate_factor']

        # Restore core scene settings
        if 'frame_start' in settings:
            scene.frame_start = settings['frame_start']
        if 'frame_end' in settings:
            scene.frame_end = settings['frame_end']
        if 'camera' in settings and settings['camera'] != "None":
            if settings['camera'] in bpy.data.objects:
                scene.camera = bpy.data.objects[settings['camera']]
            else:
                errors.append(f"Camera {settings['camera']} no longer exists")
        
        # Restore render settings
        if 'fps' in settings:
            scene.render.fps = settings['fps']
        if 'resolution_percentage' in settings:
            scene.render.resolution_percentage = settings['resolution_percentage']
        if 'filepath' in settings:
            scene.render.filepath = settings['filepath']
        
        # Restore render image settings
        if 'file_format' in settings:
            scene.render.image_settings.file_format = settings['file_format']
        if 'color_mode' in settings:
            scene.render.image_settings.color_mode = settings['color_mode']
        if 'color_depth' in settings:
            scene.render.image_settings.color_depth = settings['color_depth']
        if 'compression' in settings and hasattr(scene.render.image_settings, 'compression'):
            scene.render.image_settings.compression = settings['compression']
        
        # Restore metadata settings
        if 'use_stamp' in settings:
            scene.render.use_stamp = settings['use_stamp']
        if 'use_stamp_frame' in settings:
            scene.render.use_stamp_frame = settings['use_stamp_frame']
        if 'use_stamp_frame_range' in settings:
            scene.render.use_stamp_frame_range = settings['use_stamp_frame_range']
        if 'use_stamp_camera' in settings:
            scene.render.use_stamp_camera = settings['use_stamp_camera']
        if 'use_stamp_lens' in settings:
            scene.render.use_stamp_lens = settings['use_stamp_lens']
        if 'use_stamp_scene' in settings:
            scene.render.use_stamp_scene = settings['use_stamp_scene']
        if 'stamp_font_size' in settings:
            scene.render.stamp_font_size = settings['stamp_font_size']
        
        # Restore FFMPEG settings
        if 'ffmpeg_format' in settings:
            scene.render.ffmpeg.format = settings['ffmpeg_format']
        if 'ffmpeg_codec' in settings:
            scene.render.ffmpeg.codec = settings['ffmpeg_codec']
        if 'ffmpeg_audio_codec' in settings:
            scene.render.ffmpeg.audio_codec = settings['ffmpeg_audio_codec']
        if 'ffmpeg_constant_rate_factor' in settings:
            scene.render.ffmpeg.constant_rate_factor = settings['ffmpeg_constant_rate_factor']
        if 'ffmpeg_ffmpeg_preset' in settings:
            scene.render.ffmpeg.ffmpeg_preset = settings['ffmpeg_ffmpeg_preset']
        if 'ffmpeg_gopsize' in settings:
            scene.render.ffmpeg.gopsize = settings['ffmpeg_gopsize']
        if 'ffmpeg_use_autosplit' in settings:
            scene.render.ffmpeg.use_autosplit = settings['ffmpeg_use_autosplit']
        if 'ffmpeg_audio_channels' in settings:
            scene.render.ffmpeg.audio_channels = settings['ffmpeg_audio_channels']
        if 'ffmpeg_audio_bitrate' in settings:
            scene.render.ffmpeg.audio_bitrate = settings['ffmpeg_audio_bitrate']
        
        # Restore audio settings if they exist
        if 'audio_mixrate' in settings and hasattr(scene.render.ffmpeg, 'audio_mixrate'):
            scene.render.ffmpeg.audio_mixrate = settings['audio_mixrate']
        
        # Restore sequencer settings if they exist
        if 'use_sequencer' in settings and hasattr(scene.render, 'use_sequencer'):
            scene.render.use_sequencer = settings['use_sequencer']
        
        # Restore simplify setting
        if 'use_simplify' in settings:
            scene.render.use_simplify = settings['use_simplify']
        
        debug_log("Original settings successfully restored")
        
        if errors:
            debug_log("Some settings could not be restored:")
            for error in errors:
                debug_log(f"  - {error}")
            return False
        
        return True
        
    except Exception as e:
        debug_log(f"Error restoring settings: {e}")
        return False


class QuickPreviewQueueItem(bpy.types.PropertyGroup):
    camera_name: bpy.props.StringProperty(name="Camera Name", default="")
    frame_start: bpy.props.IntProperty(name="Start Frame", default=1)
    frame_end: bpy.props.IntProperty(name="End Frame", default=250)
    output_path: bpy.props.StringProperty(name="Output Path", default="")
    enabled: bpy.props.BoolProperty(name="Enabled", default=True)
    status: bpy.props.EnumProperty(
        name="Status",
        items=[
            ('PENDING', "Pending", "Waiting to render"),
            ('PROCESSING', "Processing", "Currently rendering"),
            ('COMPLETED', "Completed", "Finished rendering"),
            ('FAILED', "Failed", "Something went wrong")
        ],
        default='PENDING'
    )


class CameraFrameRange(PropertyGroup):
    frame_start: IntProperty(name="Start Frame", default=1)
    frame_end: IntProperty(name="End Frame", default=250)

def get_default_output_folder():
    """Get default output folder with error handling"""
    try:
        default_folder = bpy.path.abspath("//previews/")
        # If we're in a new unsaved file, bpy.path.abspath("//previews/") might return invalid path
        if default_folder.startswith("//") and not bpy.data.is_saved:
            # Use the temporary directory instead
            import tempfile
            default_folder = os.path.join(tempfile.gettempdir(), "blender_previews")
        return default_folder
    except Exception as e:
        debug_log(f"Error getting default output folder: {e}")
        import tempfile
        return os.path.join(tempfile.gettempdir(), "blender_previews")

def get_scene_name():
    """Get scene name with options for full name or simplified"""
    try:
        if bpy.data.is_saved:
            filename = bpy.path.basename(bpy.data.filepath)
            
            # Remove extension
            scene_name = os.path.splitext(filename)[0]
            
            # If full scene name is not enabled, remove version numbers
            if not bpy.context.scene.quickpreview_full_scene_name:
                # Remove version pattern like "_v001" or "-v002" or "v003" at the end of filename
                scene_name = re.sub(r'[_-]?v\d+$', '', scene_name)
            
            return scene_name
        else:
            return "untitled"
    except Exception as e:
        debug_log(f"Error getting scene name: {e}")
        return "untitled"

def load_camera_frame_range(context, camera_name):
    """Load stored frame range for the selected camera"""
    global updating
    if updating:
        return
    
    if camera_name == "VIEWPORT":
        return
    
    try:
        updating = True
        debug_log(f"Loading frame range for camera: {camera_name}")
        
        # Get stored data
        data = {}
        try:
            data = json.loads(context.scene.quickpreview_camera_ranges)
        except Exception as e:
            debug_log(f"Error loading camera data: {e}")
            return
        
        # Load frame range if we have it
        if camera_name in data:
            ranges = data[camera_name]
            context.scene.quickpreview_frame_start = ranges['start']
            context.scene.quickpreview_frame_end = ranges['end']
            debug_log(f"Loaded range {ranges['start']} - {ranges['end']} for camera {camera_name}")
        else:
            debug_log(f"No saved range found for camera {camera_name}")
    finally:
        updating = False
        debug_camera_ranges(context)

def save_camera_frame_range(context, camera_name):
    # Don't save for the viewport pseudo-camera
    if camera_name == "VIEWPORT":
        return

    try:
        # Prevent re-entrant calls while we serialize
        global updating
        updating = True

        debug_log(f"Saving frame range for camera: {camera_name}")

        # Load existing JSON data (or start fresh)
        try:
            data = json.loads(context.scene.quickpreview_camera_ranges or "{}")
        except Exception as e:
            debug_log(f"No existing data, creating new dict: {e}")
            data = {}

        # Overwrite this camera's entry
        data[camera_name] = {
            'start': context.scene.quickpreview_frame_start,
            'end':   context.scene.quickpreview_frame_end
        }

        # Write it back to the Scene property
        context.scene.quickpreview_camera_ranges = json.dumps(data)
        debug_log(
            f"Stored range {context.scene.quickpreview_frame_start} – "
            f"{context.scene.quickpreview_frame_end} for {camera_name}"
        )

    finally:
        # Always clear the lock and dump full debug info
        updating = False
        debug_camera_ranges(context)


def update_camera(self, context):
    """Change the viewport to look through selected camera and load its frame range"""
    global updating
    if updating:
        return
    
    camera_name = context.scene.quickpreview_camera
    debug_log(f"Camera changed to: {camera_name}")
    
    # Load the saved frame range for this camera
    load_camera_frame_range(context, camera_name)
    
    # Only change viewport if a specific camera is selected (not viewport)
    if camera_name != "VIEWPORT" and camera_name in bpy.data.objects:
        camera_obj = bpy.data.objects[camera_name]
        
        # Change the active camera
        context.scene.camera = camera_obj
        
        # Find 3D view and change to camera view
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        # If not already in camera view, switch to it
                        if space.region_3d.view_perspective != 'CAMERA':
                            space.region_3d.view_perspective = 'CAMERA'
                        break
                break
        
        debug_log(f"Switched viewport to camera: {camera_name}")
    
    # Add debug call outside the if statement to run for all camera selections
    debug_camera_ranges(context)
    
    # Also update the output path when camera changes
    update_output_path(self, context)

def update_frame_range(self, context):
    """Update frame range when the timeline/custom radio is changed"""
    global updating
    if updating:
        return
    
    try:
        updating = True
        
        if context.scene.quickpreview_frame_range == 'TIMELINE':
            context.scene.quickpreview_frame_start = context.scene.frame_start
            context.scene.quickpreview_frame_end = context.scene.frame_end
            debug_log(f"Updated to timeline frame range: {context.scene.frame_start}-{context.scene.frame_end}")
        
        # Save the frame range for the current camera
        camera_name = context.scene.quickpreview_camera
        save_camera_frame_range(context, camera_name)
        
        # Update output path when frame range changes
        update_output_path(self, context)
    
    finally:
        updating = False

def update_output_path(self, context):
    """Update output path based on current settings"""
    try:
        scene = context.scene
        
        # Check if this update is being triggered by a direct UI path change
        # If the path has been manually edited, don't regenerate it
        if self and hasattr(self, 'is_path_manually_edited') and self.is_path_manually_edited:
            debug_log(f"Path manually edited, keeping user path: {scene.quickpreview_output_path}")
            return
        
        # Build filename parts
        parts = []
        
        # Add scene name if option is enabled
        if scene.quickpreview_include_scene_name:
            filename_scene = get_scene_name()
            debug_log(f"Scene name determined to be: {filename_scene}")
            parts.append(filename_scene)
        
        # Add camera name if option is enabled
        if scene.quickpreview_include_camera and scene.quickpreview_camera != "VIEWPORT":
            parts.append(scene.quickpreview_camera)
        
        # Get frame range based on current settings
        frame_start = scene.quickpreview_frame_start
        frame_end = scene.quickpreview_frame_end
        
        # Add frame range
        parts.append(f"{frame_start:03d}-{frame_end:03d}")
        
        # Join parts with underscores
        basename = "_".join(parts)
        debug_log(f"Base filename: {basename}")
        
        # Determine output folder - use existing directory if path already set
        output_folder = ""
        current_path = scene.quickpreview_output_path
        
        if current_path and os.path.dirname(current_path):
            # Use the directory from the existing path if it's valid
            directory = os.path.dirname(bpy.path.abspath(current_path))
            if os.path.exists(directory):
                output_folder = directory
                debug_log(f"Using existing directory: {output_folder}")
        
        # If no valid folder found, use default
        if not output_folder:
            output_folder = get_default_output_folder()
            debug_log(f"Using default output folder: {output_folder}")
        
        # Determine file extension based on selected format
        extension = ".mov"  # Default
        if scene.quickpreview_output_format == 'MP4_H264':
            extension = ".mp4"
        elif scene.quickpreview_output_format == 'PNG_SEQ':
            extension = ".png"
        elif scene.quickpreview_output_format == 'JPEG_SEQ':
            extension = ".jpg"
        
        # For image sequences, handle differently - use #### for frame numbers
        if scene.quickpreview_output_format in ['PNG_SEQ', 'JPEG_SEQ']:
            if scene.quickpreview_save_mode == 'INCREMENTAL':
                # Add explicit underscore before frame placeholder
                output_file = f"{basename}_v001/{basename}_v001_####"
            else:
                # Add explicit underscore before frame placeholder
                output_file = f"{basename}/{basename}_####"
            
            # Set the output_path without extension - Blender will add the correct extension
            scene.quickpreview_output_path = os.path.join(output_folder, output_file)
            debug_log(f"Updated output path for image sequence: {scene.quickpreview_output_path}")
            
            # Early return to avoid adding extension below
            return
        else:
            # Video files
            if scene.quickpreview_save_mode == 'INCREMENTAL':
                output_file = f"{basename}_v001" + extension
            else:  # OVERWRITE mode
                output_file = f"{basename}" + extension
            
            # Set the final path
            scene.quickpreview_output_path = os.path.join(output_folder, output_file)
            debug_log(f"Updated output path: {scene.quickpreview_output_path}")
    
    except Exception as e:
        debug_log(f"Error in update_output_path: {e}")
        # Only set a safe default if the path is empty
        if not context.scene.quickpreview_output_path:
            import tempfile
            context.scene.quickpreview_output_path = os.path.join(tempfile.gettempdir(), "preview.mp4")
        # Save the frame range for the current camera
        camera_name = context.scene.quickpreview_camera
        save_camera_frame_range(context, camera_name)
        
        # Update output path when frame range changes
        update_output_path(self, context)
    
    finally:
        updating = False

def update_frame_start_end(self, context):
    """Called when individual frame start/end values change"""
    global updating
    if updating:
        return
    
    try:
        updating = True
        debug_log(f"Frame range changed to: {context.scene.quickpreview_frame_start} - {context.scene.quickpreview_frame_end}")
        
        # Save the frame range for the current camera
        camera_name = context.scene.quickpreview_camera
        save_camera_frame_range(context, camera_name)
        
        # Update output path when frame range changes
        update_output_path(self, context)
    
    finally:
        updating = False


def get_next_version_number(filepath, extension=".mov"):
    """Get the next version number for incremental saves"""
    try:
        directory = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        
        # Extract the base name without version and extension
        # Use the provided extension or default to .mov
        base_pattern = r'(.+?)_v\d+' + re.escape(extension) + r'$'
        match = re.match(base_pattern, filename)
        
        if match:
            basename = match.group(1)
            version_pattern = re.compile(rf"{re.escape(basename)}_v(\d+)" + re.escape(extension) + r"$")
            
            if os.path.exists(directory):
                existing_files = [f for f in os.listdir(directory)]
                versions = []
                
                for f in existing_files:
                    vmatch = version_pattern.match(f)
                    if vmatch:
                        versions.append(int(vmatch.group(1)))
                
                debug_log(f"Found versions: {versions}")
                if versions:
                    return max(versions) + 1
        
        # Default to version 1 if no matching files or pattern issues
        return 1
    
    except Exception as e:
        debug_log(f"Error finding next version: {e}")
        return 1

def update_render_progress():
    """Timer function to update render progress during OpenGL rendering"""
    scene = bpy.context.scene
    debug_log(f"Timer tick: is_rendering={scene.quickpreview_is_rendering}, progress={scene.quickpreview_progress}, frame={scene.frame_current}")
    
    
    # If we're not rendering anymore, stop the timer
    if not scene.quickpreview_is_rendering:
        debug_log("Rendering stopped, stopping timer")
        return None  # Returning None removes the timer
    
    # Calculate progress based on current frame vs. total frames
    if scene.frame_end > scene.frame_start:
        current_frame = scene.frame_current
        total_frames = scene.frame_end - scene.frame_start + 1
        

        # Calculate progress (0.0 to 1.0)
        progress = (current_frame - scene.frame_start) / total_frames
        scene.quickpreview_progress = max(0.0, min(1.0, progress))
        debug_log(f"Progress calculated: frame {current_frame}/{scene.frame_end} = {progress:.2f}")
    
        # Log progress if debug mode is on
        if DEBUG_MODE:
            old_progress = getattr(scene, '_last_logged_progress', -1)
            current_progress = scene.quickpreview_progress
    
            # Only log when progress changes significantly to avoid log spam
            if abs(current_progress - old_progress) >= 0.05:  # Log every 5% change
                debug_log(f"Render progress: Frame {current_frame}/{scene.frame_end} ({int(current_progress * 100)}%)")
                scene._last_logged_progress = current_progress
    
    # Force redraw of the interface to show updated progress
    for area in bpy.context.screen.areas:
        area.tag_redraw()  # Redraw all areas, not just 3D views
    
    # Continue the timer
    return 0.1  # Check again in 0.1 seconds

def detect_audio_sources(scene):
    """Detect available audio sources in the scene
    Returns a tuple of (has_vse_audio, has_scene_audio)"""
    
    # Check for VSE audio strips
    has_vse_audio = False
    if scene.sequence_editor and scene.sequence_editor.sequences_all:
        sound_strips = [seq for seq in scene.sequence_editor.sequences_all 
                      if seq.type in ['SOUND', 'MOVIE', 'SCENE'] and hasattr(seq, 'sound')]
        has_vse_audio = len(sound_strips) > 0
    
    # Check for speaker objects in the scene
    speaker_objects = [obj for obj in scene.objects if obj.type == 'SPEAKER']
    has_scene_audio = len(speaker_objects) > 0
    
    return has_vse_audio, has_scene_audio

class QUICKPREVIEW_OT_render(Operator):
    bl_idname = "quickpreview.render"
    bl_label = "Make Preview"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        debug_log("\n----- RENDER OPERATION DEBUG -----")
        debug_camera_ranges(context)
        debug_log("Starting Quick Preview rendering...")
        
    #  file-saved check 
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "Please save your Blender file before using Quick Preview")
            debug_log("Render cancelled - file not saved")
            return {'CANCELLED'}

        # Store settings backup
        backup_file, original_settings = store_original_settings(context)
        
        try:
            # Initialize progress tracking
            scene.quickpreview_progress = 0.0
            scene.quickpreview_is_rendering = True
            debug_log(f"Set rendering flag: is_rendering={scene.quickpreview_is_rendering}, progress={scene.quickpreview_progress}")

            # Start the progress update timer
            timer_added = False
            try:
                bpy.app.timers.register(update_render_progress)
                timer_added = True
            except Exception as e:
                debug_log(f"Failed to register timer: {e}")
        
            debug_log(f"Timer registration attempted: {timer_added}")

            # Apply the user's Simplify toggle
            scene.render.use_simplify = scene.quickpreview_use_simplify
        
            # Get initial path from settings
            init_path = bpy.path.abspath(scene.quickpreview_output_path)
        
            # Ensure we have a valid output path
            if not init_path or init_path == "":
                # If no path is set, generate one
                self_dummy = type('DummyClass', (), {'is_path_manually_edited': False})()
                update_output_path(self_dummy, context)
                init_path = bpy.path.abspath(scene.quickpreview_output_path)
                debug_log(f"No output path was set, generated: {init_path}")
            else:
                debug_log(f"Using existing output path: {init_path}")
            
            # For incremental mode, update the version number right before rendering
            if scene.quickpreview_save_mode == 'INCREMENTAL':
                directory = os.path.dirname(init_path)
                filename = os.path.basename(init_path)
                extension = os.path.splitext(filename)[1]  # Get the actual extension
                
                # If this is a template with v001, replace with actual next version
                if "_v001" in filename or "_v" not in filename:
                    # Get base name without version 
                    if "_v" in filename:
                        basename = filename.split("_v")[0]
                    else:
                        # For files without version, use filename without extension
                        basename = os.path.splitext(filename)[0]
                    
                    # Find next version - use the correct extension
                    search_pattern = os.path.join(directory, f"{basename}_v*{extension}")
                    debug_log(f"Searching for existing versions with pattern: {search_pattern}")
                    
                    # Use the correct extension
                    next_version_path = os.path.join(directory, f"{basename}_v001{extension}")
                    next_version = get_next_version_number(next_version_path, extension)
                    
                    # Create new filename with correct version and extension
                    filename = f"{basename}_v{next_version:03d}{extension}"
                    init_path = os.path.join(directory, filename)
                    debug_log(f"Updated to next version: {init_path}")
            
            # Create output directory
            full_path = init_path
            
            # Make sure the directory exists
            output_dir = os.path.dirname(full_path)
            if not os.path.exists(output_dir):
                debug_log(f"Output directory doesn't exist, creating: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            debug_log(f"Final output path for rendering: {full_path}")
            
            # Set rendering parameters for the preview - TEMPORARILY
            scene.render.filepath = full_path

           # For image sequences, ensure we have proper frame placeholders
            if scene.quickpreview_output_format in ['PNG_SEQ', 'JPEG_SEQ']:
                # Image sequence settings
                if scene.quickpreview_output_format == 'PNG_SEQ':
                    scene.render.image_settings.file_format = 'PNG'
                else:  # JPEG
                    scene.render.image_settings.file_format = 'JPEG'
                    scene.render.image_settings.quality = scene.quickpreview_image_quality
                
                # Make sure directory exists
                output_dir = os.path.dirname(full_path)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                
                # Get base filename without extension
                base_filename = os.path.splitext(os.path.basename(full_path))[0]

                # Handle incremental save mode
                if scene.quickpreview_save_mode == 'INCREMENTAL':
                    # Find existing version pattern in the base filename
                    version_match = re.search(r'_v(\d+)', base_filename)
                    if version_match:
                        # Extract current version and base name
                        current_version = int(version_match.group(1))
                        base_name = base_filename[:version_match.start()]
                        
                        # Check for existing files with this base name
                        pattern = os.path.join(output_dir, f"{base_name}_v*_0001.*")
                        try:
                            existing_files = [f for f in glob.glob(pattern)]
                            if existing_files:
                                # Find highest existing version
                                highest_version = 0
                                for file in existing_files:
                                    v_match = re.search(r'_v(\d+)_', os.path.basename(file))
                                    if v_match:
                                        v_num = int(v_match.group(1))
                                        highest_version = max(highest_version, v_num)
                                
                                # Only increment if we found existing files
                                if highest_version >= current_version:
                                    # Create new version
                                    new_version = highest_version + 1
                                    base_filename = f"{base_name}_v{new_version:03d}"
                                    debug_log(f"Incrementing to version {new_version}")
                        except Exception as e:
                            debug_log(f"Error finding existing versions: {e}")

                # Set the correct filepath format with underscore for frame numbers
                # and no extension (Blender will add it)
                scene.render.filepath = os.path.join(output_dir, f"{base_filename}_")
                
                debug_log(f"Final image sequence path: {scene.render.filepath}####")
            else:
                # Video format settings
                scene.render.image_settings.file_format = 'FFMPEG'
                
                # Set video codec and format
                if scene.quickpreview_output_format == 'MP4_H264':
                    scene.render.ffmpeg.format = 'MPEG4'
                    scene.render.ffmpeg.codec = 'H264'
                else:  # Default to MOV/H264
                    scene.render.ffmpeg.format = 'QUICKTIME'
                    scene.render.ffmpeg.codec = 'H264'
                
                # Apply quality setting - use enum values, not numeric strings
                if scene.quickpreview_video_quality == 'HIGH':
                    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
                elif scene.quickpreview_video_quality == 'MEDIUM':
                    scene.render.ffmpeg.constant_rate_factor = 'MEDIUM'
                else:  # LOW
                    scene.render.ffmpeg.constant_rate_factor = 'LOW'
            # Apply frame range from camera's stored settings
            scene.frame_start = scene.quickpreview_frame_start
            scene.frame_end = scene.quickpreview_frame_end
            debug_log(f"Using camera frame range: {scene.frame_start}-{scene.frame_end}")
            
            # Apply camera
            if scene.quickpreview_camera != "VIEWPORT" and scene.quickpreview_camera in bpy.data.objects:
                scene.camera = bpy.data.objects[scene.quickpreview_camera]
                debug_log(f"Set camera to: {scene.quickpreview_camera}")
            else:
                debug_log("Using viewport camera")
            
            # Apply framerate if override is enabled
            if scene.quickpreview_override_fps:
                scene.render.fps = scene.quickpreview_fps
                debug_log(f"Overriding FPS to: {scene.quickpreview_fps}")
            
            # Apply resolution scale if set
            if scene.quickpreview_override_resolution_scale:
                scene.render.resolution_percentage = scene.quickpreview_resolution_scale
                debug_log(f"Overriding resolution scale to: {scene.quickpreview_resolution_scale}%")

            # Apply metadata burn settings if enabled
            if scene.quickpreview_burn_metadata:
                scene.render.use_stamp = True
                scene.render.use_stamp_frame = True
                scene.render.use_stamp_frame_range = True
                scene.render.use_stamp_camera = True
                scene.render.use_stamp_lens = True
                scene.render.use_stamp_scene = True
                # Set other stamps to False
                scene.render.use_stamp_date = False
                scene.render.use_stamp_time = False
                scene.render.use_stamp_render_time = False
                scene.render.use_stamp_memory = False
                scene.render.use_stamp_hostname = False
                scene.render.use_stamp_marker = False
                scene.render.use_stamp_filename = False
                # Set font size
                scene.render.stamp_font_size = scene.quickpreview_metadata_fontsize
            else:
                # If user doesn't want burn metadata, make sure it's disabled
                scene.render.use_stamp = False

            debug_log(f"Rendering Quick Preview to: {full_path}")
            # Set audio codec
            scene.render.ffmpeg.audio_codec = 'AAC'

            # Detect audio sources
            has_vse_audio, has_scene_audio = detect_audio_sources(scene)
            debug_log(f"Audio sources detected: VSE audio: {has_vse_audio}, Scene audio: {has_scene_audio}")

            # Render with appropriate audio parameters
            if has_vse_audio:
                debug_log("Rendering with VSE audio")
                # Try to enable audio without using sequencer mode
                # Directly use FFMPEG audio settings
                scene.render.ffmpeg.audio_codec = 'AAC'
                
                # Render the viewport
                bpy.ops.render.opengl(animation=True)
                
            elif has_scene_audio:
                debug_log("Rendering with scene audio")
                # Ensure audio codec is set
                scene.render.ffmpeg.audio_codec = 'AAC'
                bpy.ops.render.opengl(animation=True)
            else:
                debug_log("No audio sources detected, rendering without audio")
                bpy.ops.render.opengl(animation=True)
            
            # Set progress to 100% after successful render
            scene.quickpreview_progress = 1.0
            debug_log(f"Render completed, setting progress to 1.0")
                
            # Open preview in video player if requested
            if scene.quickpreview_open_after_render and os.path.exists(full_path):
                self.open_file(full_path)
            
            # Open output folder if requested
            if scene.quickpreview_open_output_folder and os.path.exists(os.path.dirname(full_path)):
                open_folder(full_path)
            
            self.report({'INFO'}, f"Preview saved to: {os.path.basename(full_path)}")
            return {'FINISHED'}
            
        except Exception as e:
            # Add proper error handling here
            debug_log(f"Error during rendering: {e}")
            self.report({'ERROR'}, f"Rendering failed: {e}")
            # Reset progress on error
            scene.quickpreview_progress = 0.0
            return {'CANCELLED'}
            
        finally:
            # Clean up progress tracking
            scene.quickpreview_is_rendering = False
            debug_log(f"Rendering complete, final progress={scene.quickpreview_progress}")
            
            # Make sure to stop the timer if it's still running
            if hasattr(bpy.app, 'timers'):
                try:
                    bpy.app.timers.unregister(update_render_progress)
                    debug_log("Timer unregistered")
                except Exception as e:
                    debug_log(f"Error unregistering timer: {e}")            
            
            # CRITICAL: Restore all original settings
            debug_log("Restoring original render settings...")
            restore_success = restore_original_settings(context, original_settings)
            
            if not restore_success:
                # Settings were not fully restored - inform the user
                self.report({'WARNING'}, "Some settings may not have been completely restored. Check the console for details.")
                # Keep the backup file for manual recovery
                if backup_file:
                    debug_log(f"Settings backup preserved at {backup_file} for manual recovery")
            else:
                # If settings were successfully restored, clean up the backup file
                if backup_file and os.path.exists(backup_file):
                    try:
                        os.remove(backup_file)
                        debug_log(f"Deleted backup file: {backup_file}")
                    except Exception as e:
                        debug_log(f"Could not delete backup file: {e}")

    def open_file(self, filepath):
        """Open the file in the default system viewer"""
        try:
            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", filepath])
            else:  # Linux
                subprocess.call(["xdg-open", filepath])
            debug_log(f"Opened file in default viewer: {filepath}")
        except Exception as e:
            debug_log(f"Error opening file: {e}")

class QUICKPREVIEW_OT_set_output_path(Operator):
    bl_idname = "quickpreview.set_output_path"
    bl_label = "Set Custom Output Path"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: StringProperty(
        name="Output Path",
        description="Choose the output path for the preview",
        subtype='FILE_PATH',
    )
    
    is_path_manually_edited: BoolProperty(default=True)
    
    def execute(self, context):
        scene = context.scene
        scene.quickpreview_output_path = self.filepath
        debug_log(f"Custom output path set to: {self.filepath}")
        return {'FINISHED'}
    
    def invoke(self, context, event):
        self.filepath = context.scene.quickpreview_output_path
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class QUICKPREVIEW_PT_panel(Panel):
    bl_label = "Preview Buddy"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = ADDON_CATEGORY
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Add debug output to check progress bar condition 
        should_show_progress = scene.quickpreview_is_rendering or scene.quickpreview_progress > 0

        debug_log(f"Panel draw: is_rendering={scene.quickpreview_is_rendering}, progress={scene.quickpreview_progress}, should_show_progress={should_show_progress}")

        # Create a distinctive box for the render button 
        box = layout.box()
        # Add the Render button with extra emphasis
        row = box.row(align=True)
        row.scale_y = 2.0  # Double height
        row.operator("quickpreview.render", text="MAKE PREVIEW", icon='RENDER_ANIMATION')

        # When checking if progress bar should show
        if should_show_progress:
            debug_log("Progress bar condition met - should be drawing progress bar")

        # Add progress bar below the render button 
        if scene.quickpreview_is_rendering or scene.quickpreview_progress > 0:
            
            # Add this debug line
            debug_log("Progress bar condition met - should be drawing progress bar")
       
            # Create a row with reduced height for the progress bar
            row = layout.row()
            row.scale_y = 0.5  # Makes the progress bar 50% of normal height
            
            # Calculate percentage
            percentage = int(scene.quickpreview_progress * 100)
            
            # Display progress bar with percentage text
            row.progress(
                factor=scene.quickpreview_progress,
                type='BAR',
                text=f"{percentage}%" if scene.quickpreview_is_rendering else ""  # Removed the "Complete" text
            )

class QUICKPREVIEW_PT_camera_settings(Panel):
    bl_label = "Camera Settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = ADDON_CATEGORY
    bl_parent_id = "QUICKPREVIEW_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Camera selector
        row = layout.row()
        layout.prop(scene, "quickpreview_camera")
        
        # Add navigation buttons in a separate row
        # row = layout.row(align=True)
        # row.operator("quickpreview.prev_camera", text="", icon='TRIA_LEFT')
        # row.operator("quickpreview.next_camera", text="", icon='TRIA_RIGHT')
        
        # Frame Range settings
        layout.separator()
        layout.label(text="Frame Range")
        layout.prop(scene, "quickpreview_frame_range", text="Mode")
        
        # Show the stored ranges for each camera, with delete buttons
        try:
            data = json.loads(scene.quickpreview_camera_ranges or "{}")
            if data:
                ranges_box = layout.box()
                ranges_box.label(text="Stored Camera Ranges:")
                for cam, rng in data.items():
                    row = ranges_box.row(align=True)
                    row.label(text=f"{cam}: {rng['start']} – {rng['end']}")
                    # delete-button
                    op = row.operator(
                        "quickpreview.delete_camera_range",
                        text="",
                        icon='X',
                        emboss=False
                    )
                    op.camera_name = cam
        except Exception as e:
            debug_log(f"Error displaying camera ranges: {e}")
        
        # Custom frame range for current camera
        row = layout.row()
        row.label(text="Preview Range:")
        row = layout.row()
        row.prop(scene, "quickpreview_frame_start")
        row.prop(scene, "quickpreview_frame_end")
        
        # Show the timeline range for reference
        row = layout.row()
        row.label(text=f"Timeline Range: {scene.frame_start} - {scene.frame_end}")

class QUICKPREVIEW_PT_output_settings(Panel):
    bl_label = "Output Settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = ADDON_CATEGORY
    bl_parent_id = "QUICKPREVIEW_PT_panel"  # This makes it a subpanel
    bl_options = {'DEFAULT_CLOSED'}  # This makes it collapsed by default
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        # Format selection
        layout.label(text="Output Format:")
        layout.prop(scene, "quickpreview_output_format", text="")

        # Show appropriate quality settings based on selected format
        if scene.quickpreview_output_format in ['PNG_SEQ', 'JPEG_SEQ']:
            if scene.quickpreview_output_format == 'JPEG_SEQ':
                layout.prop(scene, "quickpreview_image_quality")
        else:
            # Video quality settings
            layout.prop(scene, "quickpreview_video_quality", text="Video Quality")

        layout.separator()
        # Use a row with a button for the output path
        row = layout.row(align=True)
        row.label(text="Output Path:")
        output_path = scene.quickpreview_output_path
        if output_path:
            # Show the directory and filename in separate labels
            try:
                directory = os.path.dirname(output_path)
                filename = os.path.basename(output_path)
                row = layout.row()
                row.label(text=f"Directory: {directory}")
                row = layout.row()
                row.label(text=f"Filename: {filename}")
            except:
                row = layout.row()
                row.label(text=output_path)
        
        # Add a button to choose the output path
        row = layout.row()
        row.operator("quickpreview.set_output_path", text="Choose Output Path", icon='FILEBROWSER')
        
        # Open After Render and Open Output Folder options
        layout.prop(scene, "quickpreview_open_after_render")
        layout.prop(scene, "quickpreview_open_output_folder")
        
        # Add a separator before other output settings
        layout.separator()
        
        # Output settings content
        row = layout.row()
        row.prop(scene, "quickpreview_include_scene_name")
        if scene.quickpreview_include_scene_name:
            row = layout.row()
            row.prop(scene, "quickpreview_full_scene_name")
        
        layout.prop(scene, "quickpreview_include_camera")
        layout.prop(scene, "quickpreview_save_mode")
        

class QUICKPREVIEW_PT_performance(Panel):
    bl_label = "Performance Overrides"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = ADDON_CATEGORY
    bl_parent_id = "QUICKPREVIEW_PT_panel"  # This makes it a subpanel
    bl_options = {'DEFAULT_CLOSED'}  # This makes it collapsed by default
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # FPS override
        row = layout.row()
        row.prop(scene, "quickpreview_override_fps", text="Override FPS")
        if scene.quickpreview_override_fps:
            layout.prop(scene, "quickpreview_fps", text="FPS")

        # Resolution override
        row = layout.row()
        row.prop(scene, "quickpreview_override_resolution_scale", text="Override Resolution Scale")
        if scene.quickpreview_override_resolution_scale:
            layout.prop(scene, "quickpreview_resolution_scale", text="Scale %")

        # Simplify toggle
        layout.prop(scene, "quickpreview_use_simplify", text="Enable Simplify")

        # Add the metadata burning options here
        layout.separator()
        layout.prop(scene, "quickpreview_burn_metadata", text="Burn Info Into Preview")
        if scene.quickpreview_burn_metadata:
            row = layout.row()
            row.prop(scene, "quickpreview_metadata_fontsize", text="Font Size")


class QUICKPREVIEW_OT_debug_panel(Operator):
    bl_idname = "quickpreview.toggle_debug"
    bl_label = "Toggle Debug Mode"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global DEBUG_MODE
        DEBUG_MODE = context.scene.quickpreview_debug_mode
        debug_log(f"Debug mode {'enabled' if DEBUG_MODE else 'disabled'}")
        return {'FINISHED'}

def update_debug_mode(self, context):
    global DEBUG_MODE
    DEBUG_MODE = context.scene.quickpreview_debug_mode
    debug_log(f"Debug mode {'enabled' if DEBUG_MODE else 'disabled'}")

class QUICKPREVIEW_OT_delete_camera_range(bpy.types.Operator):
    bl_idname = "quickpreview.delete_camera_range"
    bl_label = "Delete Stored Range"
    bl_description = "Remove this camera's saved preview range"

    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        # Load the JSON dict
        data = {}
        try:
            data = json.loads(context.scene.quickpreview_camera_ranges or "{}")
        except:
            pass

        # Remove the key if it exists
        if self.camera_name in data:
            del data[self.camera_name]
            context.scene.quickpreview_camera_ranges = json.dumps(data)
            self.report({'INFO'}, f"Deleted range for {self.camera_name}")
        else:
            self.report({'WARNING'}, f"No stored range for {self.camera_name}")

        return {'FINISHED'}


# This will be called after all addons are registered to initialize the output path
@bpy.app.handlers.persistent
def initialize_output_paths(dummy):
    """Initialize output paths for all scenes after Blender is fully loaded"""
    try:
        for scene in bpy.data.scenes:
            if not scene.quickpreview_output_path:
                # Create a context override to update the output path
                for window in bpy.context.window_manager.windows:
                    screen = window.screen
                    for area in screen.areas:
                        if area.type =='VIEW_3D':
                            override = {'window': window, 'screen': screen, 'area': area, 'scene': scene}
                            update_output_path(None, override)
                            break
    except Exception as e:
        debug_log(f"Error initializing output paths: {e}")


# ── Queue Operators & Panel ─────────────────────────────────────────────────

class QUICKPREVIEW_OT_add_to_queue(bpy.types.Operator):
    bl_idname = "quickpreview.add_to_queue"
    bl_label = "Add to Queue"
    bl_description = "Add current camera + frame range to the queue"
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):
        scene = context.scene
        item = scene.quickpreview_queue.add()
        item.camera_name = scene.quickpreview_camera
        item.frame_start  = scene.quickpreview_frame_start
        item.frame_end    = scene.quickpreview_frame_end
        item.output_path  = scene.quickpreview_output_path
        self.report({'INFO'}, f"Queued {item.camera_name} {item.frame_start}-{item.frame_end}")
        return {'FINISHED'}


class QUICKPREVIEW_OT_remove_queue_item(bpy.types.Operator):
    bl_idname = "quickpreview.remove_queue_item"
    bl_label = "Remove from Queue"
    index: bpy.props.IntProperty()

    def execute(self, context):
        q = context.scene.quickpreview_queue
        if 0 <= self.index < len(q):
            q.remove(self.index)
            self.report({'INFO'}, "Removed from queue")
        return {'FINISHED'}


class QUICKPREVIEW_OT_clear_queue(bpy.types.Operator):
    bl_idname = "quickpreview.clear_queue"
    bl_label = "Clear Queue"

    def execute(self, context):
        context.scene.quickpreview_queue.clear()
        self.report({'INFO'}, "Queue cleared")
        return {'FINISHED'}

class QUICKPREVIEW_OT_set_queue_output_path(bpy.types.Operator):
    """Choose a custom output path for this queue item"""
    bl_idname = "quickpreview.set_queue_output_path"
    bl_label = "Set Queue Output Path"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty()
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        item = context.scene.quickpreview_queue[self.index]
        self.filepath = item.output_path
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        item = context.scene.quickpreview_queue[self.index]
        item.output_path = self.filepath
        self.report({'INFO'}, f"Queue item {self.index+1} path set")
        return {'FINISHED'}

class QUICKPREVIEW_OT_process_queue(bpy.types.Operator):
    bl_idname = "quickpreview.process_queue"
    bl_label = "Process Queue"
    bl_description = "Run Quick Preview on every enabled queue item"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        queue = scene.quickpreview_queue
        if not queue:
            self.report({'WARNING'}, "Queue is empty")
            return {'CANCELLED'}

        # save original state
        orig_cam      = scene.camera
        orig_start    = scene.frame_start
        orig_end      = scene.frame_end
        orig_filepath = scene.quickpreview_output_path

        for item in queue:
            if not item.enabled:
                continue
            item.status = 'PROCESSING'
            self.report({'INFO'}, f"Rendering {item.camera_name} {item.frame_start}-{item.frame_end}")

            # apply this item’s settings
            scene.quickpreview_camera      = item.camera_name
            scene.quickpreview_frame_start = item.frame_start
            scene.quickpreview_frame_end   = item.frame_end
            scene.quickpreview_output_path = item.output_path

            # invoke your existing render operator
            result = bpy.ops.quickpreview.render('INVOKE_DEFAULT')
            item.status = 'COMPLETED' if 'FINISHED' in result else 'FAILED'

        # restore original
        scene.camera                = orig_cam
        scene.frame_start           = orig_start
        scene.frame_end             = orig_end
        scene.quickpreview_output_path = orig_filepath

        self.report({'INFO'}, "Queue complete")
        return {'FINISHED'}

class QUICKPREVIEW_OT_restore_settings(Operator):
    bl_idname = "quickpreview.restore_settings"
    bl_label = "Restore Quick Preview Settings"
    bl_description = "Restore original render settings from backup after a crash"
    
    def execute(self, context):
        # Find backup files
        temp_dir = bpy.app.tempdir
        try:
            recovery_files = [f for f in os.listdir(temp_dir) 
                             if f.startswith("quickpreview_backup_") and f.endswith(".json")]
        except Exception as e:
            self.report({'ERROR'}, f"Could not access temp directory: {e}")
            return {'CANCELLED'}
        
        if not recovery_files:
            self.report({'INFO'}, "No backup settings found")
            return {'CANCELLED'}
        
        # Load most recent backup
        latest_file = max(recovery_files, key=lambda f: os.path.getmtime(os.path.join(temp_dir, f)))
        file_path = os.path.join(temp_dir, latest_file)
        
        try:
            with open(file_path, 'r') as f:
                settings = json.load(f)
            
            # Apply all settings
            success = restore_original_settings(context, settings)
            
            if success:
                # Delete the backup file
                os.remove(file_path)
                self.report({'INFO'}, "Original settings restored successfully")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "Some settings could not be restored. Check console for details.")
                return {'FINISHED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Failed to restore settings: {e}")
            return {'CANCELLED'}

class QUICKPREVIEW_PT_queue_test(bpy.types.Panel):
    bl_label = "Render Queue"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = ADDON_CATEGORY

    def draw(self, context):
        layout = self.layout
        scene  = context.scene

        box = layout.box()
        box.label(text="Queue Management")
        row = box.row(align=True)
        row.operator("quickpreview.add_to_queue", text="Add to Queue")
        row.operator("quickpreview.clear_queue", text="Clear Queue")

        queue = scene.quickpreview_queue
        if queue:
            for i, item in enumerate(queue):
                icon = {
                    'PENDING':    'TIME',
                    'PROCESSING': 'SORTTIME',
                    'COMPLETED':  'CHECKMARK',
                    'FAILED':     'ERROR'
                }[item.status]

                # First row: item info + remove button
                row = box.row(align=True)
                row.label(
                    text=f"{i+1}. {item.camera_name} {item.frame_start}-{item.frame_end}",
                    icon=icon
                )
                remove_op = row.operator("quickpreview.remove_queue_item", text="", icon='X')
                remove_op.index = i

                # Second row: show/edit output path
                row = box.row(align=True)
                row.prop(item, "output_path", text="")
                set_path_op = row.operator(
                    "quickpreview.set_queue_output_path",
                    text="",
                    icon='FILE_FOLDER'
                )
                set_path_op.index = i
        else:
            box.label(text="Queue is empty")



        layout.separator()
        layout.operator("quickpreview.process_queue", icon='RENDER_ANIMATION')

class QUICKPREVIEW_PT_about(Panel):
    bl_label = "About"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = ADDON_CATEGORY
    bl_parent_id = "QUICKPREVIEW_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        # Version info
        col = layout.column()
        col.label(text=f"Version: {'.'.join(str(x) for x in bl_info['version'])}")
        col.label(text=f"Author: {bl_info['author']}")
        
        # Add donation button with fun text
        col.separator()
        col.label(text="Enjoying Preview Buddy?")
        row = col.row()
        row.scale_y = 1.5  # Make button bigger
        row.operator("wm.url_open", text="☕ Support My Coffee Addiction", icon='HEART').url = "https://ko-fi.com/bentebent"
        
        # Support info
        col.separator()
        row = col.row()
        row.operator("wm.url_open", text="filmicart.com").url = "https://filmicart.com"
              
# ───────────────────────────────────────────────────────────────────────────────

@bpy.app.handlers.persistent
def check_for_recovery_files(dummy):
    """Check for settings backup files on startup"""
    try:
        temp_dir = bpy.app.tempdir
        recovery_files = [f for f in os.listdir(temp_dir) 
                         if f.startswith("quickpreview_backup_") and f.endswith(".json")]
        
        if recovery_files and bpy.context.window_manager:
            # Show a popup notice to the user
            def draw_recovery_notice(self, context):
                layout = self.layout
                layout.label(text="Quick Preview found unsaved settings from a previous session.")
                layout.label(text="Your render settings may need to be restored.")
                layout.operator("quickpreview.restore_settings")
            
            # Use a timer to show the popup after Blender is fully loaded
            def show_recovery_popup():
                bpy.context.window_manager.popup_menu(draw_recovery_notice, 
                                                    title="Settings Recovery", 
                                                    icon='RECOVER_LAST')
                return None  # Don't repeat the timer
            
            bpy.app.timers.register(show_recovery_popup, first_interval=1.0)
            
    except Exception as e:
        debug_log(f"Error checking for recovery files: {e}")

def register():
    
    # 1) Register PropertyGroups first (dependencies)
    bpy.utils.register_class(CameraFrameRange)
    bpy.utils.register_class(QuickPreviewQueueItem)
    
    # 2) Register Operators
    bpy.utils.register_class(QUICKPREVIEW_OT_render)
    bpy.utils.register_class(QUICKPREVIEW_OT_set_output_path)
    bpy.utils.register_class(QUICKPREVIEW_OT_debug_panel)
    bpy.utils.register_class(QUICKPREVIEW_OT_delete_camera_range)
    bpy.utils.register_class(QUICKPREVIEW_OT_restore_settings)
    bpy.utils.register_class(QUICKPREVIEW_OT_add_to_queue)
    bpy.utils.register_class(QUICKPREVIEW_OT_remove_queue_item)
    bpy.utils.register_class(QUICKPREVIEW_OT_clear_queue)
    bpy.utils.register_class(QUICKPREVIEW_OT_set_queue_output_path)
    bpy.utils.register_class(QUICKPREVIEW_OT_process_queue)
    
  # Set panel ordering with bl_order
    QUICKPREVIEW_PT_queue_test.bl_order = 0           # First position (render queue)
    QUICKPREVIEW_PT_camera_settings.bl_order = 1      # Second position
    QUICKPREVIEW_PT_panel.bl_order = 2                # Third position (main panel/button)
    QUICKPREVIEW_PT_output_settings.bl_order = 3      # Fourth position
    QUICKPREVIEW_PT_performance.bl_order = 4          # Fifth position
    QUICKPREVIEW_PT_about.bl_order = 5                # Last position
   

    # 3) Register Panels 
    bpy.utils.register_class(QUICKPREVIEW_PT_queue_test)
    bpy.utils.register_class(QUICKPREVIEW_PT_panel)
    bpy.utils.register_class(QUICKPREVIEW_PT_camera_settings)
    bpy.utils.register_class(QUICKPREVIEW_PT_output_settings)
    bpy.utils.register_class(QUICKPREVIEW_PT_performance)
    bpy.utils.register_class(QUICKPREVIEW_PT_about)

   
    # 4) Register all of your Scene-level properties
    # Add progress tracking properties
    bpy.types.Scene.quickpreview_progress = bpy.props.FloatProperty(
        name="Render Progress",
        description="Tracks the current render progress",
        min=0.0, max=1.0,
        default=0.0
    )
    
    bpy.types.Scene.quickpreview_is_rendering = bpy.props.BoolProperty(
        name="Is Rendering",
        description="Indicates if a render is in progress",
        default=False
    )
   
   # Performance: Simplify toggle
    bpy.types.Scene.quickpreview_use_simplify = BoolProperty(
        name="Use Simplify",
        description="Enable Blender's Simplify for faster previews",
        default=False
    )
   
    bpy.types.Scene.quickpreview_burn_metadata = BoolProperty(
        name="Burn Info into Preview",
        description="Overlay camera, frame and scene info on the preview",
        default=True
    )

    bpy.types.Scene.quickpreview_metadata_fontsize = IntProperty(
        name="Font Size",
        description="Size of the metadata text",
        default=24,  # larger default
        min=8, max=64
    )

    bpy.types.Scene.quickpreview_debug_mode = BoolProperty(
        name="Debug Mode",
        description="Enable debug logging for Quick Preview",
        default=DEBUG_MODE,
        update=update_debug_mode
    )

    bpy.types.Scene.quickpreview_output_path = StringProperty(
        name="Output Path",
        description="Final preview file path",
        subtype='FILE_PATH',
        default=""
    )

    bpy.types.Scene.quickpreview_camera_ranges = StringProperty(
        name="Camera Ranges Data",
        description="Internal storage for camera frame ranges (JSON)",
        default="{}"
    )

    bpy.types.Scene.quickpreview_frame_ranges = CollectionProperty(type=CameraFrameRange)

    bpy.types.Scene.quickpreview_frame_range = EnumProperty(
        name="Frame Range",
        items=[
            ('TIMELINE', "Timeline", "Use the current timeline frame range"),
            ('CUSTOM',   "Custom",   "Use custom frame range")
        ],
        default='TIMELINE',
        update=update_frame_range
    )

    bpy.types.Scene.quickpreview_camera = EnumProperty(
        name="Camera",
        items=lambda self, context: [("VIEWPORT","Active Viewport","")] +
            [(cam.name, cam.name, "") for cam in bpy.data.objects if cam.type=='CAMERA'],
        update=update_camera
    )

    bpy.types.Scene.quickpreview_include_camera = BoolProperty(
        name="Include Camera Name",
        description="Include camera name in filename",
        default=True,
        update=update_output_path
    )

    bpy.types.Scene.quickpreview_include_scene_name = BoolProperty(
        name="Include Scene Name",
        description="Include scene name in filename",
        default=True,
        update=update_output_path
    )

    bpy.types.Scene.quickpreview_full_scene_name = BoolProperty(
        name="Include Version in Scene Name",
        description="Keep version suffix in scene name",
        default=False,
        update=update_output_path
    )

    bpy.types.Scene.quickpreview_save_mode = EnumProperty(
        name="Save Mode",
        items=[
            ('INCREMENTAL', "Incremental Save", "Save new versions"),
            ('OVERWRITE',   "Overwrite",        "Replace previous file")
        ],
        default='INCREMENTAL',
        update=update_output_path
    )

    bpy.types.Scene.quickpreview_frame_start = IntProperty(
        name="Start Frame",
        default=1,
        update=update_frame_start_end
    )

    bpy.types.Scene.quickpreview_frame_end = IntProperty(
        name="End Frame",
        default=250,
        update=update_frame_start_end
    )

    bpy.types.Scene.quickpreview_override_fps = BoolProperty(
        name="Override FPS",
        description="Override the scene framerate for the preview",
        default=False
    )

    bpy.types.Scene.quickpreview_fps = IntProperty(
        name="FPS",
        default=30,
        min=1, max=120
    )

    bpy.types.Scene.quickpreview_override_resolution_scale = BoolProperty(
        name="Override Resolution Scale",
        description="Override the resolution percentage for the preview",
        default=False
    )

    bpy.types.Scene.quickpreview_resolution_scale = IntProperty(
        name="Resolution Scale",
        default=50,
        min=1, max=100,
        subtype='PERCENTAGE'
    )

    bpy.types.Scene.quickpreview_open_after_render = BoolProperty(
        name="Open After Render",
        description="Open the preview in default video player after rendering",
        default=False
    )

    bpy.types.Scene.quickpreview_open_output_folder = BoolProperty(
        name="Open Output Folder",
        description="Open the output folder after rendering",
        default=False
    )

    # Add these properties near the end of your register() function, 
    # before the handlers and after your other property definitions

    bpy.types.Scene.quickpreview_output_format = EnumProperty(
        name="Output Format",
        items=[
            ('MP4_H264', "MP4 (H.264)", "Save as MP4 with H.264 codec - most compatible format"),
            ('MOV_H264', "QuickTime (H.264)", "Save as QuickTime MOV with H.264 codec"),
            ('PNG_SEQ', "PNG Sequence", "Save as individual PNG files for each frame"),
            ('JPEG_SEQ', "JPEG Sequence", "Save as individual JPEG files for each frame"),
        ],
        default='MP4_H264',
        update=update_output_path
    )

    bpy.types.Scene.quickpreview_video_quality = EnumProperty(
        name="Video Quality",
        items=[
            ('HIGH', "High Quality", "Higher quality, larger file size"),
            ('MEDIUM', "Medium Quality", "Balanced quality and file size"),
            ('LOW', "Low Quality", "Lower quality, smaller file size")
        ],
        default='MEDIUM'
    )

    bpy.types.Scene.quickpreview_image_quality = IntProperty(
        name="Image Quality",
        description="Quality for JPEG images (ignored for PNG)",
        min=0, max=100,
        default=90
    )

    bpy.types.Scene.quickpreview_queue = bpy.props.CollectionProperty(type=QuickPreviewQueueItem)


    # 5) Hook in the persistent handlers
    bpy.app.handlers.load_post.append(initialize_output_paths)
    bpy.app.handlers.load_post.append(check_for_recovery_files)

    # 6) Initialize output paths right now (if Blender already has a scene)
    try:
        if hasattr(bpy.context, 'scene'):
            initialize_output_paths(None)
    except Exception:
        pass


def unregister():

    # 1) Remove handlers first (if you have any)
    if initialize_output_paths in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(initialize_output_paths)
    if check_for_recovery_files in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(check_for_recovery_files)

    # Delete scene properties
    del bpy.types.Scene.quickpreview_queue
    del bpy.types.Scene.quickpreview_debug_mode
    del bpy.types.Scene.quickpreview_output_path
    del bpy.types.Scene.quickpreview_camera_ranges
    del bpy.types.Scene.quickpreview_frame_ranges
    del bpy.types.Scene.quickpreview_frame_range
    del bpy.types.Scene.quickpreview_camera
    del bpy.types.Scene.quickpreview_include_camera
    del bpy.types.Scene.quickpreview_include_scene_name
    del bpy.types.Scene.quickpreview_full_scene_name
    del bpy.types.Scene.quickpreview_save_mode
    del bpy.types.Scene.quickpreview_frame_start
    del bpy.types.Scene.quickpreview_frame_end
    del bpy.types.Scene.quickpreview_override_fps
    del bpy.types.Scene.quickpreview_fps
    del bpy.types.Scene.quickpreview_override_resolution_scale
    del bpy.types.Scene.quickpreview_resolution_scale
    del bpy.types.Scene.quickpreview_open_after_render
    del bpy.types.Scene.quickpreview_open_output_folder
    del bpy.types.Scene.quickpreview_use_simplify
    del bpy.types.Scene.quickpreview_progress
    del bpy.types.Scene.quickpreview_is_rendering
    del bpy.types.Scene.quickpreview_output_format
    del bpy.types.Scene.quickpreview_video_quality
    del bpy.types.Scene.quickpreview_image_quality
    del bpy.types.Scene.quickpreview_burn_metadata
    del bpy.types.Scene.quickpreview_metadata_fontsize

    # 3) Unregister Panels (reverse order)
    bpy.utils.unregister_class(QUICKPREVIEW_PT_about)
    bpy.utils.unregister_class(QUICKPREVIEW_PT_performance)
    bpy.utils.unregister_class(QUICKPREVIEW_PT_output_settings)
    bpy.utils.unregister_class(QUICKPREVIEW_PT_camera_settings)
    bpy.utils.unregister_class(QUICKPREVIEW_PT_panel)
    bpy.utils.unregister_class(QUICKPREVIEW_PT_queue_test)

    # 4) Unregister Operators (reverse order)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_process_queue)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_set_queue_output_path)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_clear_queue)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_remove_queue_item)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_add_to_queue)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_restore_settings)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_delete_camera_range)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_debug_panel)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_set_output_path)
    bpy.utils.unregister_class(QUICKPREVIEW_OT_render)
    
    # 5) Unregister PropertyGroups last
    bpy.utils.unregister_class(QuickPreviewQueueItem)
    bpy.utils.unregister_class(CameraFrameRange)
    


if __name__ == "__main__":
    register()