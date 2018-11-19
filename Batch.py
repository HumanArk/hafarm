import os, sys
import utils
import const
from uuid import uuid4
from HaGraph import HaGraphItem
from HaGraph import HaGraphDependency

class BatchBase(HaGraphItem):

    def __init__(self, name, tags, *args, **kwargs):
        """
        Kwargs:
            job_name (str): 
        """
        index = str(uuid4())
        name = name
        tags = tags
        path = ''
        dependencies = []
        super(BatchBase, self).__init__(index, dependencies, name, path, tags, *args, **kwargs)
        self.parms['ignore_check'] = True
        self.parms['slots'] = 1
        self.parms['req_resources'] = ''
        self.parms['start_frame'] = 1
        self.parms['end_frame'] = 1
        self.parms['job_name'] = kwargs.get('job_name', self._generate_unique_job_name())

    def _generate_unique_job_name(self, name = 'no_name_job'):
        """Returns unique name for a job. 'Name' is usually a scene file. 
        """
        from base64 import urlsafe_b64encode
        name = os.path.basename(name)
        return '_'.join([os.path.split(name)[1], urlsafe_b64encode(os.urandom(3))])


class BatchMp4(BatchBase):

    def __init__(self, filename, *args, **kwargs):
        name = 'ffmpeg'
        tags = '/hafarm/ffmpeg'
        super(BatchMp4, self).__init__(name, tags, *args, **kwargs)
        scene_file_path, _, _, _ = utils.padding(filename, 'nuke')
        base, file = os.path.split(scene_file_path)
        file, _ = os.path.splitext(file)
        inputfile = os.path.join(base, const.PROXY_POSTFIX, file + '.jpg')
        outputfile = os.path.join(base, utils.padding(filename)[0] + 'mp4')
        self.parms['command_arg'] = ['-y -r 25 -i %s -an -vcodec libx264 -vpre slow -crf 26 -threads 1 %s' % (inputfile, outputfile)]
        self.parms['command'] << {'command': 'ffmpeg '}


class BatchDebug(BatchBase):

    def __init__(self, filename, *args, **kwargs):
        """
        Args:
            filename (str): 
        Kwargs:
            start (int): 
            end (int):
        """
        name = 'debug_images.py'
        tags = '/hafarm/debug_images'
        super(BatchDebug, self).__init__(name, tags, *args, **kwargs)
        self.parms['command_arg'] = ['']
        self.parms['start_frame'] = kwargs.get('start', 1)
        self.parms['end_frame'] = kwargs.get('end', 1)
        scene_file_path, _, frame_padding_length, ext = utils.padding(filename)
        path, file = os.path.split(filename)
        path = os.path.join(path, const.DEBUG_POSTFIX)
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except OSError as why:
                print why

        self.parms['scene_file'] = scene_file_path + const.TASK_ID_PADDED + ext
        self.parms['command'] << {'command': '$HAFARM_HOME/scripts/debug_images.py --job %s --save_json -i ' % self.parms['job_name']}
        self.parms['frame_padding_length'] = int(frame_padding_length)


class BatchReportsMerger(BatchBase):
    """ Merges previously generated debug reports per frame, and do various things
        with that, send_emials, save on dist as json/html etc.
    """

    def __init__(self, filename, *args, **kwargs):
        """
        Args:
            filename (str): 
        Kwargs:
            resend_frames (bool): Current state to be in.
            ifd_path
            mad_threshold (float):
        """
        name = 'generate_render_report.py'
        tags = '/hafarm/generate_render_report'
        super(BatchReportsMerger, self).__init__(name, tags, *args, **kwargs)
        resend_frames = kwargs.get('resend_frames', False)
        ifd_path = kwargs.get('ifd_path')
        mad_threshold = kwargs.get('mad_threshold', 5.0)
        send_email = '--send_email'
        ifd_path = '--ifd_path %s' % ifd_path if ifd_path else ''
        resend_frames = '--resend_frames' if resend_frames else ''
        path, filename = os.path.split(filename)
        scene_file_path, _, _, _ = utils.padding(filename, 'shell')
        log_path = os.path.join(path, const.DEBUG_POSTFIX)
        self.parms['scene_file'] = os.path.join(log_path, scene_file_path) + '.json'
        self.parms['command'] << {'command': '$HAFARM_HOME/scripts/generate_render_report.py %s %s %s --mad_threshold %s --save_html ' % (send_email,
                     ifd_path,
                     resend_frames,
                     mad_threshold)}


class BatchJoinTiles(BatchBase):
    """Creates a command specificly for merging tiled rendering with oiiotool."""

    def __init__(self, filename, tiles_x, tiles_y, mask_filename, priority, *args, **kwargs):
        """
        Args:
            filename (str):
            tiles_x (int):
            tiles_y (int):
        Kwargs:
            start (int): 
            end (int): 
            make_proxy (bool):
        """
        name = 'merge_tiles.py'
        tags = '/hafarm/merge_tiles'
        super(BatchJoinTiles, self).__init__(name, tags, *args, **kwargs)
        self.parms['output_picture'] = filename
        self.parms['scene_file'] = mask_filename
        self.parms['priority'] = priority
        self.parms['slots'] = 0
        self.parms['start_frame'] = kwargs.get('start',1)
        self.parms['end_frame'] = kwargs.get('end',1)
        self.parms['make_proxy'] = kwargs.get('make_proxy', False)
        start = kwargs.get('start', 1)
        end = kwargs.get('end', 1)
        
        self.parms['command_arg'] = [
                                        '-x %s' % tiles_x 
                                        ,'-y %s' % tiles_y 
                                        ,'-f %s' % const.TASK_ID 
                                        ,'-o %s' % filename
                                        ,'-m %s' % mask_filename
                                ]
                                
        self.parms['command'] << {'command': 'rez env oiio -- python $HAFARM_HOME/scripts/merge_tiles.py' }


