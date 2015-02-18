import os, sys
import ha

# Custom: 
from ha.hafarm import HaFarm
from ha.hafarm import utils
from ha.hafarm import const


# For some reason this can't be in its own module for now and we'd like to
# use it across the board, so I put it here. At some point, we should remove haSGE inheritance
# making it more like a plugin class. At that point, this problem should be reviewed.
class BatchFarm(HaFarm):
    '''Performs arbitrary script on farm. Also encapsulates utility functions for handling usual tasks.
    like tile merging, dubuging renders etc.'''
    def __init__(self, job_name='', parent_job_name=[], queue='', command='', command_arg=''):
        super(BatchFarm, self).__init__()
        self.parms['queue']          = queue
        self.parms['job_name']       = job_name
        self.parms['command']        = command
        self.parms['command_arg']    = [command_arg]
        self.parms['hold_jid']       = parent_job_name
        self.parms['ignore_check']   = True
        self.parms['slots']          = 1
        self.parms['req_resources'] = ''

    def join_tiles(self, filename, start, end, ntiles):
        '''Creates a command specificly for merging tiled rendering with oiiotool.'''
        from ha.path import padding

        # Retrive full frame name (without _tile%i)
        if const.TILE_ID in filename:
            base, rest = filename.split(const.TILE_ID)
            tmp, ext   = os.path.splitext(filename)
            filename   = base + ext
        else:
            base, ext  = os.path.splitext(filename)


        details = padding(filename, format='nuke')
        base    = os.path.splitext(details[0])[0]
        base, file = os.path.split(base)
        base    = os.path.join(base, const.TILES_POSTFIX, file)
        reads   = [base + const.TILE_ID + '%s' % str(tile) + ext for tile in range(ntiles)]


        # Reads:
        command = ' '
        command += '%s ' % reads[0]
        command += '%s ' % reads[1]
        command += '--over ' 

        for read in reads[2:]:
            command += "%s " % read
            command += '--over ' 

        # Final touch:
        command += '-o %s ' % details[0]
        command += '--frames %s-%s ' % (start, end)

        # Additional path for proxy images (to be created from joined tiles)
        if self.parms['make_proxy']:
            path, file = os.path.split(details[0])
            path = os.path.join(path, const.PROXY_POSTFIX)

            # FIXME: It shouldn't be here at all. 
            if not os.path.isdir(path): os.mkdir(path)

            proxy    = os.path.join(path, os.path.splitext(file)[0] + '.jpg')
            command += '--tocolorspace "sRGB" -ch "R,G,B" -o %s ' % proxy

        self.parms['command_arg'] = [command]
        self.parms['command']     = const.OIIOTOOL      
        self.parms['start_frame'] = 1
        self.parms['end_frame']   = 1 
        return command

    def debug_images(self, filename):
        '''By using iinfo utility inspect filename (usually renders).'''
        from ha.path import padding
        details = padding(filename, 'shell')
        self.parms['command'] = const.IINFO
        self.parms['command_arg'] =  ['`ls %s | grep -v "%s" ` | grep File ' % (details[0], const.TILE_ID)]
        self.parms['start_frame'] = 1
        self.parms['end_frame']   = 1
        self.parms['email_stdout'] = True

    def make_movie(self, filename):
        '''Make a movie from custom files. '''
        from ha.path import padding

        # Input filename with proxy correction:
        details = padding(filename, 'nuke')
        base, file = os.path.split(details[0])
        file, ext  = os.path.splitext(file)
        inputfile  = os.path.join(base, const.PROXY_POSTFIX, file + '.jpg')
        outputfile = os.path.join(base, padding(filename)[0] + 'mp4')
        command = "-y -r 25 -i %s -an -vcodec libx264 %s" % (inputfile, outputfile)
        self.parms['command'] = 'ffmpeg '
        self.parms['command_arg'] = [command]
        self.parms['start_frame'] = 1
        self.parms['end_frame']   = 1