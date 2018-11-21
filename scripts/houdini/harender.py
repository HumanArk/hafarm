import hou
from optparse import OptionParser
import sys, os
from hafarm import utils

# Global overwrites
HAFARM_DISABLE_VECTORIZE_EXPORT = "HAFARM_DISABLE_VECTORIZE_EXPORT" in os.environ

def help():
    return 'harender: Houdinis hrender csh script replacement.\
        \n\tusage: harender [-f "1 100" -i 1 -] -d /out/mantra1 myscene.hip \
        \n Alternatively frame list may be specifid with -l (-l 1-3,4,5,6,7-12x2)'


def parseOptions():
    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    parser.add_option("-d", "--driver", dest="driver",  action="store", type="string", help="ROP driver to render.")
    parser.add_option("-f", "--frame_range", dest="frame_range",  action="store", type="int", nargs=2, help="Frames range to render (-f 1 100)")
    parser.add_option("-i", "--increment", dest="increment",  action="store", type="int", default=1, help="Frames imcrement.")
    parser.add_option("-j", "--threads", dest="threads",  action="store", type="int", default=1, help="Controls multithreading.")
    parser.add_option("-l", "--frame_list", dest="frame_list",  action="store",  help="Alternative ")
    parser.add_option("", "--ignore_tiles", dest='ignore_tiles', action='store_true', default=False, help="Disables tiling on Mantra Rop (This allow custom ifd filtering setup).")
    parser.add_option("", "--generate_ifds", dest='generate_ifds', action='store_true', default=False, help="Changes Rop setting to save IFD files on disk. ")
    parser.add_option("", "--ifd_path", dest='ifd_path', action='store', default='$JOB/render/sungrid/ifd', help="Overwrites default IFD path.")
    parser.add_option("", "--vectorize_export", dest='vectorize_export', action='store',  type="string", default="msk_*", help="Makes sure all deep rasters matching given pattern will be vector type.")
    parser.add_option("", "--save_scene", dest='save_scene', action='store',  type="string", default="", help="Saves modified version of a scene mostly for debugging purposes.")
    parser.add_option("", "--idle", dest='idle', action='store_true', default=False, help="Run the script, but don't render anything.")
    parser.add_option("", "--scratch", dest='scratch', action='store', default="/SCRATCH/temp", help="Default location for storing temp render data per job.")
    parser.add_option("", "--ifd_name", dest='ifd_name', action='store', default=None, help="Overwrites default IFD path.")
    
    (opts, args) = parser.parse_args(sys.argv[1:])
    (opts, args) = parser.parse_args(sys.argv[1:])
    return opts, args


def recursiveFindLockedParent(node):
    """ Find a locked parent containing given node.
    """
    if not node.parent():
        return None
    if not node.isLockedHDA():
        node = recursiveFindLockedParent(node.parent())
    return node


def vectorize_export(pattern, driver):
    """ Makes sure given channels are vector type.
    """
    from fnmatch import fnmatch
    binds_nodes = []
    exports = []
    variable_names = []
    VECTOR_BIND_VOP_TYPE = 7

    if driver.type().name() in ('ifd', "baketexture", "baketexture::3.0"):
        exports += [parm for parm in driver.parms()\
         if fnmatch(parm.evalAsString(), pattern)]

    for plane in exports:
        plane_name = plane.name().split("_")[-1]
        vex_name   = "vm_vextype_" + plane_name
        driver.parm(vex_name).set("vector")
        variable_names += [plane.evalAsString()]

    # Find export node inside Shaders:
    shaders = hou.node("/obj").recursiveGlob("*", filter=hou.nodeTypeFilter.Shop)

    for node in shaders:
        # Filter all but binds nodes, with export name matching current ROP
        # and active (exportparm set to 1 or 2)
        binds = [n for n in node.allSubChildren() if n.type().name() == 'bind']
        binds = [n for n in binds if n.parm("parmname").eval() in variable_names \
            and n.parm("exportparm").eval() != 0]

        # No matching exports? Go next shader. 
        if not binds:
            continue
            
        # Is it locked?
        if node.isLockedHDA():
            node.allowEditingOfContents()
        # inside locked asset:
        elif node.isInsideLockedHDA():
            parent = recursiveFindLockedParent(node)
            assert(parent)
            parent.allowEditingOfContents()
            
        # Edit shaders:
        for node in binds:
            assert(not node.isInsideLockedHDA()) # This not should be the case, but just in case.
            node.parm("parmtype").set(VECTOR_BIND_VOP_TYPE)
            node.parmTuple("vectordef").set((1,1,1))

def create_scratch_dir(scratch_parent, job_path):
    """ Create scratch dir per job.
        TODO: This shouldn't be probably here. 
        Better to move it to the app sending job.
    """
    import time
    scratch  = os.path.join(scratch_parent, job_path)
    try:
        if not os.path.isdir(scratch):
            os.mkdir(scratch)
    except:
        # This is highly concurrent, lets wait a little
        time.sleep(2)
        if not os.path.isdir(scratch):
            print "ERROR: Can't create scratch %s for a job: %s" % (scratch, hip_name)
            # now this is wrong...
            return False
        else:
            pass
    return scratch

def main():
    """Replacement for Houdini's own hrender script. Basic functions for rendering specified rop. 
       Main difference (reason to replace  hrender) was to allow rendring a list of randomly selected frames.
    """
    options, args     = parseOptions()

    if len(sys.argv) < 3:
        print help()
        sys.exit()

    # As we keep similarity to hredner, 
    # last argument of command line is a hip file. 
    scene_file = sys.argv[-1]

    print options, args
    #sys.exit()

    # Catch errors:
    if not os.path.isfile(scene_file):
        print "Can't find %s scene file." % scene_file
        return 1
    try:
        hou.hipFile.load(scene_file, True, True)
    except:
        print "Can't open %s" % scene_file
        sys.exit()
    try:
        driver = hou.node(options.driver)
    except:
        print "Can't find %s rop" % options.driver
        sys.exit()

    # Ignoring tiling:
    if options.ignore_tiles and driver.parm("vm_tile_render"):
        driver.parm("vm_tile_render").set(0)

    # Setting network starage, this will need more work soon 
    # FIXME: remove me
    job_current = os.getenv("JOB_CURRENT", None)
    job_group   = os.getenv("JOB_ASSET_TYPE", None)
    job_name    = os.getenv("JOB_ASSET_NAME", None)
    if not job_current or not job_group or not job_name:
        print "ERROR: Can't render on farm without setting on job."
        sys.exit()
    hip_path, hip_file = os.path.split(scene_file)
    job_path = "_".join((job_current, job_group, job_name, hip_file))
    tmp_shared_storage = create_scratch_dir(options.scratch, job_path)
    if not tmp_shared_storage:
        print "Warning!: Render without scratch. Something is wrong..."
        tmp_shared_storage = options.ifd_path

    print "Setting up scratch storage into: %s" % tmp_shared_storage
    if driver.parm("vm_tmpsharedstorage"):
        driver.parm("vm_tmpsharedstorage").set(tmp_shared_storage)

    # We also disable temporarly checkpoints (FIXME):
    if driver.parm("vm_writecheckpoint"):
        driver.parm("vm_writecheckpoint").set(0)

    # Change ROP to save IFD to disk:
    if driver.type().name() in ('ifd', "baketexture", 'baketexture::3.0') and options.generate_ifds:
        driver.parm("soho_outputmode").set(1)
        scene_path, scene_name = os.path.split(hou.hipFile.name())
        scene_name, ext = os.path.splitext(scene_name)
        ifd_name = os.path.join(options.ifd_path, scene_name + ".$F.ifd")
        driver.parm('soho_diskfile').set(ifd_name)

        if options.ifd_name:
            ifd_name = os.path.join(options.ifd_path, options.ifd_name + ".$F.ifd")
            ifd_name = os.path.expandvars(ifd_name)
            driver.parm('soho_diskfile').set(ifd_name)

    #Redshift pass:
    if driver.type().name() == 'Redshift_ROP' and options.generate_ifds:
        driver.parm("RS_archive_enable").set(1)
        scene_path, scene_name = os.path.split(hou.hipFile.name())
        scene_name, ext = os.path.splitext(scene_name)
        # (should we use scratch or ifd_path for rs?)
        rs_name = os.path.join(options.ifd_path, scene_name + ".$F.rs")
        driver.parm('RS_archive_file').set(rs_name)

        if options.ifd_name:
            ifd_name = os.path.join(options.ifd_path, options.ifd_name + ".$F.rs")
            driver.parm('RS_archive_file').set(ifd_name)

    # vectorize exports:
    if options.vectorize_export and not HAFARM_DISABLE_VECTORIZE_EXPORT:
        vectorize_export(options.vectorize_export, driver)

    if options.save_scene:
        try:
            hou.hipFile.save(file_name=options.save_scene)
        except:
            print "Error: Can't save a scene: ", 
            print options.save_scene

    if options.idle:
        print "Warning: Idle mode, no rendering performed."
        sys.exit()

    # Render with all details specified in a hip file:
    if not options.frame_list:
        frame_range = tuple(options.frame_range + (options.increment,))
        driver.render(frame_range=frame_range, ignore_inputs=True, verbose=True)
    # Or render from a list of random frames:
    else:
        for frame in utils.expand_sequence_into_digits(options.frame_list):
            driver.render(frame_range=(frame, frame), ignore_inputs=True, verbose=True)


        

if __name__ == '__main__': main()
