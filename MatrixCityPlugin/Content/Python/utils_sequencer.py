from typing import *
from pydantic_model import SequenceKey

import unreal
from utils import *
from utils_actor import *
import math
import numpy as np
import random

################################################################################
# misc

def convert_frame_rate_to_fps(frame_rate: unreal.FrameRate) -> float:
    return frame_rate.numerator / frame_rate.denominator


def get_sequence_fps(sequence: unreal.LevelSequence) -> float:
    seq_fps: unreal.FrameRate = sequence.get_display_rate()
    return convert_frame_rate_to_fps(seq_fps)
    

def get_animation_length(animation_asset: unreal.AnimSequence, seq_fps: Optional[float]=None) -> int:
    anim_len = animation_asset.get_editor_property("number_of_sampled_frames")

    if seq_fps:
        anim_frame_rate = animation_asset.get_editor_property("target_frame_rate")
        anim_frame_rate = convert_frame_rate_to_fps(anim_frame_rate)
        if anim_frame_rate != seq_fps:
            anim_len = round(animation_asset.get_editor_property("sequence_length") * seq_fps)

    return anim_len


################################################################################
# sequencer session
def get_transform_channels_from_section(
    trans_section: unreal.MovieScene3DTransformSection,
) -> List[unreal.MovieSceneScriptingChannel]:
    channel_x = channel_y = channel_z = channel_roll = channel_pitch = channel_yaw = None
    for channel in trans_section.get_channels():
        channel: unreal.MovieSceneScriptingChannel
        if channel.channel_name == "Location.X":
            channel_x = channel
        elif channel.channel_name == "Location.Y":
            channel_y = channel
        elif channel.channel_name == "Location.Z":
            channel_z = channel
        elif channel.channel_name == "Rotation.X":
            channel_roll = channel
        elif channel.channel_name == "Rotation.Y":
            channel_pitch = channel
        elif channel.channel_name == "Rotation.Z":
            channel_yaw = channel
    assert channel_x is not None
    assert channel_y is not None
    assert channel_z is not None
    assert channel_roll is not None
    assert channel_pitch is not None
    assert channel_yaw is not None

    return channel_x, channel_y, channel_z, channel_roll, channel_pitch, channel_yaw

def set_transform_by_section(
    trans_section: unreal.MovieScene3DTransformSection,
    loc: Tuple[float, float, float],
    rot: Tuple[float, float, float],
    key_frame: int = 0,
    key_type: str = "CONSTANT",
) -> None:
    """set `loc & rot` keys to given `transform section`

    Args:
        trans_section (unreal.MovieScene3DTransformSection): section
        loc (tuple): location key
        rot (tuple): rotation key
        key_frame (int): frame of the key. Defaults to 0.
        key_type (str): type of the key. Defaults to 'CONSTANT'. Choices: 'CONSTANT', 'LINEAR', 'AUTO'.
    """

    channel_x, channel_y, channel_z, \
        channel_roll, channel_pitch, channel_yaw = get_transform_channels_from_section(trans_section)

    loc_x, loc_y, loc_z = loc
    rot_x, rot_y, rot_z = rot

    key_frame_ = unreal.FrameNumber(key_frame)
    key_type_ = getattr(unreal.MovieSceneKeyInterpolation, key_type)
    channel_x.add_key(key_frame_, loc_x, interpolation=key_type_)
    channel_y.add_key(key_frame_, loc_y, interpolation=key_type_)
    channel_z.add_key(key_frame_, loc_z, interpolation=key_type_)
    channel_roll.add_key(key_frame_, rot_x, interpolation=key_type_)
    channel_pitch.add_key(key_frame_, rot_y, interpolation=key_type_)
    channel_yaw.add_key(key_frame_, rot_z, interpolation=key_type_)


def set_transforms_by_section(
    trans_section: unreal.MovieScene3DTransformSection,
    trans_keys: List[SequenceKey], 
    key_type: str = "CONSTANT",
) -> None:
    """set `loc & rot` keys to given `transform section`

    Args:
        trans_section (unreal.MovieScene3DTransformSection): section
        trans_dict (dict): keys
        type (str): type of the key. Defaults to 'CONSTANT'. Choices: 'CONSTANT', 'LINEAR', 'AUTO'.

    Examples:
        >>> sequence = unreal.load_asset('/Game/Sequences/NewSequence')
        >>> camera_binding = sequence.add_spawnable_from_class(unreal.CameraActor)
        >>> transform_track: unreal.MovieScene3DTransformTrack = camera_binding.add_track(unreal.MovieScene3DTransformTrack)
        >>> transform_section: unreal.MovieScene3DTransformSection = transform_track.add_section()
        >>> trans_dict = {
        >>>     0: [                    # time of key
        >>>         [500, 1500, 100],   # location of key
        >>>         [0, 0, 30]          # rotation of key
        >>>     ],
        >>>     300: [                     # multi-keys
        >>>         [1000, 2000, 300],
        >>>         [0, 0, 0]
        >>>     ]
        >>> }
        >>> set_transforms_by_section(transform_section, trans_dict)
    """

    channel_x, channel_y, channel_z, \
        channel_roll, channel_pitch, channel_yaw = get_transform_channels_from_section(trans_section)
    key_type_ = getattr(unreal.MovieSceneKeyInterpolation, key_type)

    for trans_key in trans_keys:
        key_frame = trans_key.frame
        loc_x, loc_y, loc_z = trans_key.location
        rot_x, rot_y, rot_z = trans_key.rotation

        key_time_ = unreal.FrameNumber(key_frame)
        channel_x.add_key(key_time_, loc_x, interpolation=key_type_)
        channel_y.add_key(key_time_, loc_y, interpolation=key_type_)
        channel_z.add_key(key_time_, loc_z, interpolation=key_type_)
        channel_roll.add_key(key_time_, rot_x, interpolation=key_type_)
        channel_pitch.add_key(key_time_, rot_y, interpolation=key_type_)
        channel_yaw.add_key(key_time_, rot_z, interpolation=key_type_)


def set_transform_by_binding(
    binding: unreal.SequencerBindingProxy,
    loc: Tuple[float, float, float],
    rot: Tuple[float, float, float],
    key_frame: int = 0,
    key_type: str = "CONSTANT",
) -> None:
    trans_track: unreal.MovieScene3DTransformTrack = binding.find_tracks_by_type(
        unreal.MovieScene3DTransformTrack)[0]
    trans_section = trans_track.get_sections()[0]
    set_transform_by_section(trans_section, loc, rot, key_frame, key_type)


def set_transform_by_key(
    sequence: unreal.MovieSceneSequence,
    key: str,
    loc: Tuple[float, float, float],
    rot: Tuple[float, float, float],
    key_frame: int = 0,
    key_type: str = "CONSTANT",
) -> None:
    binding: unreal.SequencerBindingProxy = sequence.find_binding_by_name(key)
    set_transform_by_binding(binding, loc, rot, key_frame, key_type)


def add_property_bool_track_to_binding(
    binding: unreal.SequencerBindingProxy,
    property_name: str,
    property_value: bool,
    bool_track: Optional[unreal.MovieSceneBoolTrack] = None,
) -> unreal.MovieSceneBoolTrack:

    if bool_track is None:
        # add bool track
        bool_track: unreal.MovieSceneBoolTrack = binding.add_track(unreal.MovieSceneBoolTrack)
        bool_track.set_property_name_and_path(property_name, property_name)

    # add bool section, and set it to extend the whole sequence
    bool_section = bool_track.add_section()
    bool_section.set_start_frame_bounded(0)
    bool_section.set_end_frame_bounded(0)

    # set key
    for channel in bool_section.find_channels_by_type(unreal.MovieSceneScriptingBoolChannel):
        channel.set_default(property_value)
    
    return bool_track


def add_property_int_track_to_binding(
    binding: unreal.SequencerBindingProxy,
    property_name: str,
    property_value: int,
    int_track: Optional[unreal.MovieSceneIntegerTrack] = None,
) -> unreal.MovieSceneIntegerTrack:

    if int_track is None:
        # add int track
        int_track: unreal.MovieSceneIntegerTrack = binding.add_track(unreal.MovieSceneIntegerTrack)
        int_track.set_property_name_and_path(property_name, property_name)

    # add int section, and set it to extend the whole sequence
    int_section = int_track.add_section()
    int_section.set_start_frame_bounded(0)
    int_section.set_end_frame_bounded(0)

    # set key
    for channel in int_section.find_channels_by_type(unreal.MovieSceneScriptingIntegerChannel):
        channel.set_default(property_value)
    
    return int_track


def add_property_float_track_to_binding(
    binding: unreal.SequencerBindingProxy,
    property_name: str,
    property_value: float,
    float_track: Optional[unreal.MovieSceneFloatTrack] = None,
) -> unreal.MovieSceneFloatTrack:
    if float_track is None:
        # add float track
        float_track: unreal.MovieSceneFloatTrack = binding.add_track(unreal.MovieSceneFloatTrack)
        float_track.set_property_name_and_path(property_name, property_name)

    # add float section, and set it to extend the whole sequence
    float_section = float_track.add_section()
    float_section.set_start_frame_bounded(0)
    float_section.set_end_frame_bounded(0)

    # set key
    for channel in float_section.find_channels_by_type(unreal.MovieSceneScriptingFloatChannel):
        channel.set_default(property_value)
    
    return float_section


def add_transform_to_binding(
    binding: unreal.SequencerBindingProxy,
    actor_loc: Tuple[float, float, float],
    actor_rot: Tuple[float, float, float],
    seq_end_frame: int,
    seq_start_frame: int=0,
    time: int = 0,
    key_type: str = "CONSTANT",
) -> unreal.MovieScene3DTransformTrack:
    """Add a transform track to the binding, and add one key at `time` to the track.

    Args:
        binding (unreal.SequencerBindingProxy): The binding to add the track to.
        actor_loc (Tuple[float, float, float]): The location of the actor.
        actor_rot (Tuple[float, float, float]): The rotation of the actor.
        seq_end_frame (int): The end frame of the sequence.
        seq_start_frame (int, optional): The start frame of the sequence. Defaults to 0.
        time (int, optional): The time of the key. Defaults to 0.
        key_type (str, optional): The type of the key. Defaults to "CONSTANT".

    Returns:
        transform_track (unreal.MovieScene3DTransformTrack): The transform track.
    """

    transform_track: unreal.MovieScene3DTransformTrack = binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section: unreal.MovieScene3DTransformSection = transform_track.add_section()
    transform_section.set_end_frame(seq_end_frame)
    transform_section.set_start_frame(seq_start_frame)
    set_transform_by_section(transform_section, actor_loc, actor_rot, time, key_type)

    return transform_track


def add_transforms_to_binding(
    binding: unreal.SequencerBindingProxy,
    actor_trans_keys: List[SequenceKey],
    key_type: str = "CONSTANT",
) -> unreal.MovieScene3DTransformTrack:

    transform_track: unreal.MovieScene3DTransformTrack = binding.add_track(unreal.MovieScene3DTransformTrack)
    transform_section: unreal.MovieScene3DTransformSection = transform_track.add_section()
    # set infinite
    transform_section.set_start_frame_bounded(0)
    transform_section.set_end_frame_bounded(0)
    # add keys
    set_transforms_by_section(transform_section, actor_trans_keys, key_type)

    return transform_track


def add_animation_to_binding(
    binding: unreal.SequencerBindingProxy,
    animation_asset: unreal.AnimSequence,
    animation_length: Optional[int]=None,
    seq_fps: Optional[float]=None,
) -> None:
    animation_track: unreal.MovieSceneSkeletalAnimationTrack = binding.add_track(
        track_type=unreal.MovieSceneSkeletalAnimationTrack
    )
    animation_section: unreal.MovieSceneSkeletalAnimationSection = animation_track.add_section()
    animation_length_ = get_animation_length(animation_asset, seq_fps)
    if animation_length is None:
        animation_length = animation_length_
    if animation_length > animation_length_:
        unreal.log_error(f"animation: '{animation_asset.get_name()}' length is too short, it will repeat itself!")

    params = unreal.MovieSceneSkeletalAnimationParams()
    params.set_editor_property("Animation", animation_asset)
    animation_section.set_editor_property("Params", params)
    animation_section.set_range(0, animation_length)


def get_spawnable_actor_from_binding(
    sequence: unreal.MovieSceneSequence,
    binding: unreal.SequencerBindingProxy,
) -> unreal.Actor:

    binds = unreal.Array(unreal.SequencerBindingProxy)
    binds.append(binding)

    bound_objects: List[unreal.SequencerBoundObjects] = unreal.SequencerTools.get_bound_objects(
        get_world(), 
        sequence, 
        binds, 
        sequence.get_playback_range()
    )

    actor = bound_objects[0].bound_objects[0]
    return actor

################################################################################
# high level functions

def add_level_visibility_to_sequence(
    sequence: unreal.LevelSequence, 
    seq_length: Optional[int]=None,
) -> None:

    if seq_length is None:
        seq_length = sequence.get_playback_end()

    # add master track (level visibility) to sequence
    level_visibility_track: unreal.MovieSceneLevelVisibilityTrack = sequence.add_master_track(unreal.MovieSceneLevelVisibilityTrack)
    # add level visibility section
    level_visible_section: unreal.MovieSceneLevelVisibilitySection = level_visibility_track.add_section()
    level_visible_section.set_visibility(unreal.LevelVisibility.VISIBLE)
    level_visible_section.set_start_frame(-1)
    level_visible_section.set_end_frame(seq_length)

    level_hidden_section: unreal.MovieSceneLevelVisibilitySection = level_visibility_track.add_section()
    level_hidden_section.set_row_index(1)
    level_hidden_section.set_visibility(unreal.LevelVisibility.HIDDEN)
    level_hidden_section.set_start_frame(-1)
    level_hidden_section.set_end_frame(seq_length)
    return level_visible_section, level_hidden_section


def add_level_to_sequence(
    sequence: unreal.LevelSequence, 
    persistent_level_path: str, 
    new_level_path: str,
    seq_fps: Optional[float]=None,
    seq_length: Optional[int]=None,
) -> None:
    """creating a new level which contains the persistent level as sub-levels.
    `CAUTION`: this function can't support `World Partition` type level which is new in unreal 5.
        No warning/error would be printed if `World partition` is used, but it will not work.

    Args:
        sequence (unreal.LevelSequence): _description_
        persistent_level_path (str): _description_
        new_level_path (str): _description_
        seq_fps (Optional[float], optional): _description_. Defaults to None.
        seq_length (Optional[int], optional): _description_. Defaults to None.
    """

    # get sequence settings
    if seq_fps is None:
        seq_fps = get_sequence_fps(sequence)
    if seq_length is None:
        seq_length = sequence.get_playback_end()

    # create a new level to place actors
    success = new_world(new_level_path)
    print(f"new level: '{new_level_path}' created: {success}")
    assert success, RuntimeError("Failed to create level")

    level_visible_names, level_hidden_names = add_levels(persistent_level_path, new_level_path)
    level_visible_section, level_hidden_section = add_level_visibility_to_sequence(sequence, seq_length)

    # set level visibility
    level_visible_section.set_level_names(level_visible_names)
    level_hidden_section.set_level_names(level_hidden_names)

    # set created level as current level
    world = get_world()
    levels = get_levels(world)
    unreal.SF_BlueprintFunctionLibrary.set_level(world, levels[0])
    save_current_level()


def add_spawnable_camera_to_sequence(
    sequence: unreal.LevelSequence,
    camera_trans: List[SequenceKey],
    camera_class: Type[unreal.CameraActor]=unreal.CameraActor,
    camera_fov: float=90.,
    seq_length: Optional[int]=None,
    key_type: str="CONSTANT",
) -> None:

    # get sequence settings
    if seq_length is None:
        seq_length = sequence.get_playback_end()

    # create a camera actor & add it to the sequence
    camera_binding = sequence.add_spawnable_from_class(camera_class)
    camera_actor = get_spawnable_actor_from_binding(sequence, camera_binding)
    camera_component_binding = sequence.add_possessable(camera_actor.camera_component)
    camera_component_binding.set_parent(camera_binding)

    # set the camera FOV
    add_property_float_track_to_binding(camera_component_binding, 'FieldOfView', camera_fov)

    # add master track (camera) to sequence
    camera_cut_track = sequence.add_master_track(unreal.MovieSceneCameraCutTrack)

    # add a camera cut track for this camera, make sure the camera cut is stretched to the -1 mark
    camera_cut_section = camera_cut_track.add_section()
    camera_cut_section.set_start_frame(-1)
    camera_cut_section.set_end_frame(seq_length)

    # set the camera cut to use this camera
    camera_binding_id = unreal.MovieSceneObjectBindingID()
    camera_binding_id.set_editor_property("Guid", camera_binding.get_id())
    camera_cut_section.set_editor_property("CameraBindingID", camera_binding_id)

    # camera_binding_id = sequence.make_binding_id(camera_binding, unreal.MovieSceneObjectBindingSpace.LOCAL)
    # camera_cut_section.set_camera_binding_id(camera_binding_id)

    # set the camera location and rotation
    add_transforms_to_binding(camera_binding, camera_trans, key_type)


def add_spawnable_actor_to_sequence(
    sequence: unreal.LevelSequence,
    actor_asset: Union[unreal.SkeletalMesh, unreal.StaticMesh],
    actor_trans: List[SequenceKey],
    actor_id: Optional[str]=None,
    actor_stencil_value: int=1,
    animation_asset: Optional[unreal.AnimSequence]=None,
    seq_fps: Optional[float]=None,
    seq_length: Optional[int]=None,
    key_type: str="CONSTANT",
) -> unreal.Actor:

    # get sequence settings
    if seq_fps is None:
        seq_fps = get_sequence_fps(sequence)
    if seq_length is None:
        seq_length = get_animation_length(animation_asset, seq_fps)

    # add actor to sequence
    actor_binding = sequence.add_spawnable_from_instance(actor_asset)
    actor = get_spawnable_actor_from_binding(sequence, actor_binding)

    # mesh_component = actor.skeletal_mesh_component
    mesh_component = get_actor_mesh_component(actor)
    mesh_component_binding = sequence.add_possessable(mesh_component)

    # set stencil value
    add_property_bool_track_to_binding(mesh_component_binding, 'bRenderCustomDepth', True)
    add_property_int_track_to_binding(mesh_component_binding, 'CustomDepthStencilValue', actor_stencil_value)

    if actor_id:
        actor_binding.set_name(actor_id)

    # add transform
    add_transforms_to_binding(actor_binding, actor_trans, key_type)

    # add animation
    if animation_asset:
        add_animation_to_binding(actor_binding, animation_asset, seq_length, seq_fps)
    
    return actor


def generate_sequence(
    sequence_dir: str, 
    sequence_name: str, 
    seq_fps: float,
    seq_length: int,
) -> unreal.LevelSequence:

    asset_tools: unreal.AssetTools = unreal.AssetToolsHelpers.get_asset_tools()  # type: ignore
    new_sequence: unreal.LevelSequence = asset_tools.create_asset(
        sequence_name,
        sequence_dir,
        unreal.LevelSequence,
        unreal.LevelSequenceFactoryNew(),
    )
    assert (new_sequence is not None), f"Failed to create LevelSequence: {sequence_dir}, {sequence_name}"
    # Set sequence config
    new_sequence.set_display_rate(unreal.FrameRate(seq_fps))
    new_sequence.set_playback_end(seq_length)

    return new_sequence

def generate_train_box(line1, line2, z, current_frame):
    
    x11, y11, x12, y12=line1
    x21, y21, x22, y22=line2
    assert(y11==y12)
    assert(y21==y22)
    assert(x11==x21)
    assert(x12==x22)
    w=math.dist([x11, y11], [x12, y12])
    h=math.dist([x11, y11], [x21, y21])
    interval=4000 # train interval
    w_instance=int(w/interval)+2
    h_instance=int(h/interval)+1
    x_start=np.linspace(x11, x12, w_instance)
    y_start=np.linspace(y11, y12, w_instance)
    x_end=np.linspace(x21, x22, w_instance)
    y_end=np.linspace(y21, y22, w_instance)
    camera_trans=[]
    
    # train
    if z>25000:
        pitch=-60
    else:
        pitch=-45
    for i in range(w_instance):
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_start[i], y_start[i], z),
            rotation=(0, pitch, 0)
            )
        )
        current_frame=current_frame+h_instance
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_end[i], y_end[i], z),
            rotation=(0, pitch, 0)
            )
        )
        current_frame=current_frame+1
    for i in range(w_instance):
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_start[i], y_start[i], z),
            rotation=(0, pitch, 90)
            )
        )
        current_frame=current_frame+h_instance
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_end[i], y_end[i], z),
            rotation=(0, pitch, 90)
            )
        )
        current_frame=current_frame+1
    for i in range(w_instance):
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_start[i], y_start[i], z),
            rotation=(0, pitch, 180)
            )
        )
        current_frame=current_frame+h_instance
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_end[i], y_end[i], z),
            rotation=(0, pitch, 180)
            )
        )
        current_frame=current_frame+1
    for i in range(w_instance):
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_start[i], y_start[i], z),
            rotation=(0, pitch, 270)
            )
        )
        current_frame=current_frame+h_instance
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_end[i], y_end[i], z),
            rotation=(0, pitch, 270)
            )
        )
        current_frame=current_frame+1
    return camera_trans, current_frame

def generate_test_box(line1, line2, z, current_frame):
    
    x11, y11, x12, y12=line1
    x21, y21, x22, y22=line2
    assert(y11==y12)
    assert(y21==y22)
    assert(x11==x21)
    assert(x12==x22)
    w=math.dist([x11, y11], [x12, y12])
    h=math.dist([x11, y11], [x21, y21])
    interval=4501 # test interval
    w_instance=int(w/interval)+2
    h_instance=int(h/interval)+1
    x_start=np.linspace(x11, x12, w_instance)
    y_start=np.linspace(y11, y12, w_instance)
    x_end=np.linspace(x21, x22, w_instance)
    y_end=np.linspace(y21, y22, w_instance)
    camera_trans=[]
    
    # test
    for i in range(w_instance):
        pitch=np.random.randint(-60,-44,size=1)
        yaw=np.random.randint(0,361,size=1)
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_start[i], y_start[i], z),
            rotation=(0, pitch, yaw)
            )
        )
        current_frame=current_frame+h_instance
        camera_trans.append( 
            SequenceKey(
            frame=current_frame, 
            location=(x_end[i], y_end[i], z),
            rotation=(0, pitch, yaw)
            )
        )
        current_frame=current_frame+1
    return camera_trans, current_frame
    

def generate_train_line(point1, point2, z, yaw, current_frame, dense=False):

    distance=math.dist(point1, point2)
    if dense==True:
        instance=int(distance/100)+1 # dense
    else:
        instance=int(distance/500)+1 # sparse

    camera_trans=[]
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 0, yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 0, yaw)
        )
    )
    current_frame=current_frame+1
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 0, 90+yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 0, 90+yaw)
        )
    )
    current_frame=current_frame+1
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 0, 180+yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 0, 180+yaw)
        )
    )
    current_frame=current_frame+1
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 0, 270+yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 0, 270+yaw)
        )
    )
    current_frame=current_frame+1
    # camera_trans.append(
    #     SequenceKey(
    #         frame=current_frame, 
    #         location=(point1[0], point1[1], z),
    #         rotation=(0, -90, yaw)
    #     )
    # )
    # current_frame=current_frame+instance
    # camera_trans.append(
    #     SequenceKey(
    #         frame=current_frame, 
    #         location=(point2[0], point2[1], z),
    #         rotation=(0, -90, yaw)
    #     )
    # )
    # current_frame=current_frame+1
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 90, yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 90, yaw)
        )
    )
    current_frame=current_frame+1
    return camera_trans, current_frame

def generate_test_line(point1, point2, z, yaw, current_frame):
    # for test
    point1[0]=point1[0]+math.cos(math.radians(yaw))*570
    point1[1]=point1[1]+math.sin(math.radians(yaw))*570
    point2[0]=point2[0]-math.cos(math.radians(yaw))*570
    point2[1]=point2[1]-math.sin(math.radians(yaw))*570
    yaw=np.random.randint(0,90,size=1)

    distance=math.dist(point1, point2)
    instance = int(distance/4830)+1 # test

    camera_trans=[]
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 0, yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 0, yaw)
        )
    )
    current_frame=current_frame+1
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 0, 90+yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 0, 90+yaw)
        )
    )
    current_frame=current_frame+1
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 0, 180+yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 0, 180+yaw)
        )
    )
    current_frame=current_frame+1
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 0, 270+yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 0, 270+yaw)
        )
    )
    current_frame=current_frame+1
    # camera_trans.append(
    #     SequenceKey(
    #         frame=current_frame, 
    #         location=(point1[0], point1[1], z),
    #         rotation=(0, -90, yaw)
    #     )
    # )
    # current_frame=current_frame+instance
    # camera_trans.append(
    #     SequenceKey(
    #         frame=current_frame, 
    #         location=(point2[0], point2[1], z),
    #         rotation=(0, -90, yaw)
    #     )
    # )
    # current_frame=current_frame+1
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point1[0], point1[1], z),
            rotation=(0, 90, yaw)
        )
    )
    current_frame=current_frame+instance
    camera_trans.append(
        SequenceKey(
            frame=current_frame, 
            location=(point2[0], point2[1], z),
            rotation=(0, 90, yaw)
        )
    )
    current_frame=current_frame+1
    return camera_trans, current_frame


def main():
    from datetime import datetime

    # pre-defined
    level = '/Game/Maps/Small_City_LVL'
    sequence_dir = '/Game/Sequences'
    seq_fps = 30
    current_frame=0
    
    # exmaples for generating training and testing set for aerial data
    sequence_name='aerial_train'
    fov=45
    camera_trans, current_frame=generate_train_box([-100000, 0, -12000, 0], [-100000, 38000, -12000, 38000], 15000, current_frame) # block 1

    # sequence_name='aerial_test'
    # fov=45
    # camera_trans, current_frame=generate_test_box([-95000, 5000,-17000, 5000], [-95000, 33000, -17000, 33000], 15000, current_frame) # block 1 test

    # exmaples for generating training(sparse/dense) and testing set for street data
    # sequence_name='street_train'
    # fov=90
    # camera_trans=[]
    # tmp_camera_trans, current_frame=generate_train_line([-85151.664062, 7755.524902], [-18491.283203, 46241.914062], 300, 30, current_frame)
    # camera_trans.extend(tmp_camera_trans)
    # tmp_camera_trans, current_frame=generate_train_line([-19102.925781, 46310.578125], [-10849.427734, 49813.980469], 300, 23, current_frame)
    # camera_trans.extend(tmp_camera_trans)

    # sequence_name='street_train_dense'
    # fov=90
    # camera_trans=[]
    # tmp_camera_trans, current_frame=generate_train_line([-85151.664062, 7755.524902], [-18491.283203, 46241.914062], 300, 30, current_frame, dense=True)
    # camera_trans.extend(tmp_camera_trans)
    # tmp_camera_trans, current_frame=generate_train_line([-19102.925781, 46310.578125], [-10849.427734, 49813.980469], 300, 23, current_frame, dense=True)
    # camera_trans.extend(tmp_camera_trans)
    
    # sequence_name='street_test'
    # fov=90
    # camera_trans=[]
    # tmp_camera_trans, current_frame=generate_test_line([-85151.664062, 7755.524902], [-18491.283203, 46241.914062], 300, 30, current_frame)
    # camera_trans.extend(tmp_camera_trans)
    # tmp_camera_trans, current_frame=generate_test_line([-19102.925781, 46310.578125], [-10849.427734, 49813.980469], 300, 23, current_frame)
    # camera_trans.extend(tmp_camera_trans)

    seq_length=current_frame
    new_sequence = generate_sequence(sequence_dir, sequence_name, seq_fps, seq_length)

    add_spawnable_camera_to_sequence(
        new_sequence, 
        camera_trans=camera_trans,
        camera_class=unreal.CineCameraActor,
        camera_fov=fov,
        seq_length=seq_length,
        key_type="LINEAR"
    )

    unreal.EditorAssetLibrary.save_loaded_asset(new_sequence, False)

    return level, f'{sequence_dir}/{sequence_name}'


if __name__ == "__main__":
    main()
