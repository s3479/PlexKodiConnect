# -*- coding: utf-8 -*-

#################################################################################################

import shutil
import xml.etree.ElementTree as etree

import xbmc
import xbmcaddon
import xbmcvfs

import clientinfo
import utils

#################################################################################################


class VideoNodes(object):


    def __init__(self):

        clientInfo = clientinfo.ClientInfo()
        self.addonName = clientInfo.getAddonName()

        self.kodiversion = int(xbmc.getInfoLabel("System.BuildVersion")[:2])

    def logMsg(self, msg, lvl=1):

        className = self.__class__.__name__
        utils.logMsg("%s %s" % (self.addonName, className), msg, lvl)


    def commonRoot(self, order, label, tagname, roottype=1):

        if roottype == 0:
            # Index
            root = etree.Element('node', attrib={'order': "%s" % order})
        elif roottype == 1:
            # Filter
            root = etree.Element('node', attrib={'order': "%s" % order, 'type': "filter"})
            etree.SubElement(root, 'match').text = "all"
            # Add tag rule
            rule = etree.SubElement(root, 'rule', attrib={'field': "tag", 'operator': "is"})
            etree.SubElement(rule, 'value').text = tagname
        else:
            # Folder
            root = etree.Element('node', attrib={'order': "%s" % order, 'type': "folder"})

        etree.SubElement(root, 'label').text = label
        etree.SubElement(root, 'icon').text = "special://home/addons/plugin.video.plexkodiconnect/icon.png"

        return root

    def viewNode(self, indexnumber, tagname, mediatype, viewtype, delete=False):

        kodiversion = self.kodiversion

        # mediatype conversion
        # LEFT: Plex wording, right: Kodi wording
        mediaTypeConversion = {
            'movie': 'movies',
            'show': 'tvshows'
        }
        mediatype = mediaTypeConversion[mediatype]
        if mediatype == "homevideos":
            # Treat homevideos as movies
            mediatype = "movies"

        cleantagname = utils.normalize_nodes(tagname.encode('utf-8'))
        if viewtype == "mixed":
            dirname = "%s - %s" % (cleantagname, mediatype)
        else:
            dirname = cleantagname
        
        path = xbmc.translatePath("special://profile/library/video/").decode('utf-8')
        nodepath = xbmc.translatePath(
                    "special://profile/library/video/plex%s/" % dirname).decode('utf-8')

        # Verify the video directory
        if not xbmcvfs.exists(path):
            shutil.copytree(
                src=xbmc.translatePath("special://xbmc/system/library/video").decode('utf-8'),
                dst=xbmc.translatePath("special://profile/library/video").decode('utf-8'))
            xbmcvfs.exists(path)

        # Create the node directory
        if not xbmcvfs.exists(nodepath):
            # We need to copy over the default items
            xbmcvfs.mkdirs(nodepath)
        else:
            if delete:
                dirs, files = xbmcvfs.listdir(nodepath)
                for file in files:
                    xbmcvfs.delete(nodepath + file)

                self.logMsg("Sucessfully removed videonode: %s." % tagname, 1)
                return

        # Create index entry
        nodeXML = "%sindex.xml" % nodepath
        # Set windows property
        path = "library://video/plex%s/" % dirname
        for i in range(1, indexnumber):
            # Verify to make sure we don't create duplicates
            if utils.window('Emby.nodes.%s.index' % i) == path:
                return

        utils.window('Emby.nodes.%s.index' % indexnumber, value=path)
        # Root
        root = self.commonRoot(order=0, label=tagname, tagname=tagname, roottype=0)
        try:
            utils.indent(root)
        except: pass
        etree.ElementTree(root).write(nodeXML)


        nodetypes = {

            '1': "all",
            '2': "recent",
            '3': "recentepisodes",
            '4': "inprogress",
            '5': "inprogressepisodes",
            '6': "unwatched",
            '7': "nextepisodes",
            '8': "sets",
            '9': "genres",
            '10': "random",
            '11': "recommended"
        }
        mediatypes = {
            # label according to nodetype per mediatype
            'movies': {
                '1': tagname,
                '2': 30174,
                '4': 30177,
                '6': 30189,
                '8': 20434,
                '9': 135,
                '10': 30229,
                '11': 30230},

            'tvshows': {
                '1': tagname,
                '2': 30170,
                '3': 30175,
                '4': 30171,
                '5': 30178,
                '7': 30179,
                '9': 135,
                '10': 30229,
                '11': 30230},
        }

        nodes = mediatypes[mediatype]
        for node in nodes:

            nodetype = nodetypes[node]
            nodeXML = "%s%s_%s.xml" % (nodepath, cleantagname, nodetype)
            # Get label
            stringid = nodes[node]
            if node != '1':
                label = utils.language(stringid)
                if not label:
                    label = xbmc.getLocalizedString(stringid)
            else:
                label = stringid

            # Set window properties
            if nodetype == "nextepisodes":
                # Custom query
                path = "plugin://plugin.video.plexkodiconnect/?id=%s&mode=nextup&limit=25" % tagname
            elif kodiversion == 14 and nodetype == "recentepisodes":
                # Custom query
                path = "plugin://plugin.video.plexkodiconnect/?id=%s&mode=recentepisodes&limit=25" % tagname
            elif kodiversion == 14 and nodetype == "inprogressepisodes":
                # Custom query
                path = "plugin://plugin.video.plexkodiconnect/?id=%s&mode=inprogressepisodes&limit=25"% tagname
            else:
                path = "library://video/plex%s/%s_%s.xml" % (dirname, cleantagname, nodetype)
            windowpath = "ActivateWindow(Video,%s,return)" % path
            
            if nodetype == "all":

                if viewtype == "mixed":
                    templabel = dirname
                else:
                    templabel = label

                embynode = "Emby.nodes.%s" % indexnumber
                utils.window('%s.title' % embynode, value=templabel)
                utils.window('%s.path' % embynode, value=windowpath)
                utils.window('%s.content' % embynode, value=path)
                utils.window('%s.type' % embynode, value=mediatype)
            else:
                embynode = "Emby.nodes.%s.%s" % (indexnumber, nodetype)
                utils.window('%s.title' % embynode, value=label)
                utils.window('%s.path' % embynode, value=windowpath)
                utils.window('%s.content' % embynode, value=path)

            if xbmcvfs.exists(nodeXML):
                # Don't recreate xml if already exists
                continue


            # Create the root
            if nodetype == "nextepisodes" or (kodiversion == 14 and
                                        nodetype in ('recentepisodes', 'inprogressepisodes')):
                # Folder type with plugin path
                root = self.commonRoot(order=node, label=label, tagname=tagname, roottype=2)
                etree.SubElement(root, 'path').text = path
                etree.SubElement(root, 'content').text = "episodes"
            else:
                root = self.commonRoot(order=node, label=label, tagname=tagname)
                if nodetype in ('recentepisodes', 'inprogressepisodes'):
                    etree.SubElement(root, 'content').text = "episodes"
                else:
                    etree.SubElement(root, 'content').text = mediatype

                limit = "25"
                # Elements per nodetype
                if nodetype == "all":
                    etree.SubElement(root, 'order', {'direction': "ascending"}).text = "sorttitle"
                
                elif nodetype == "recent":
                    etree.SubElement(root, 'order', {'direction': "descending"}).text = "dateadded"
                    etree.SubElement(root, 'limit').text = limit
                    rule = etree.SubElement(root, 'rule', {'field': "playcount", 'operator': "is"})
                    etree.SubElement(rule, 'value').text = "0"
                
                elif nodetype == "inprogress":
                    etree.SubElement(root, 'rule', {'field': "inprogress", 'operator': "true"})
                    etree.SubElement(root, 'limit').text = limit

                elif nodetype == "genres":
                    etree.SubElement(root, 'order', {'direction': "ascending"}).text = "sorttitle"
                    etree.SubElement(root, 'group').text = "genres"
                
                elif nodetype == "unwatched":
                    etree.SubElement(root, 'order', {'direction': "ascending"}).text = "sorttitle"
                    rule = etree.SubElement(root, "rule", {'field': "playcount", 'operator': "is"})
                    etree.SubElement(rule, 'value').text = "0"

                elif nodetype == "sets":
                    etree.SubElement(root, 'order', {'direction': "ascending"}).text = "sorttitle"
                    etree.SubElement(root, 'group').text = "sets"

                elif nodetype == "random":
                    etree.SubElement(root, 'order', {'direction': "ascending"}).text = "random"
                    etree.SubElement(root, 'limit').text = limit

                elif nodetype == "recommended":
                    etree.SubElement(root, 'order', {'direction': "descending"}).text = "rating"
                    etree.SubElement(root, 'limit').text = limit
                    rule = etree.SubElement(root, 'rule', {'field': "playcount", 'operator': "is"})
                    etree.SubElement(rule, 'value').text = "0"
                    rule2 = etree.SubElement(root, 'rule',
                        attrib={'field': "rating", 'operator': "greaterthan"})
                    etree.SubElement(rule2, 'value').text = "7"

                elif nodetype == "recentepisodes":
                    # Kodi Isengard, Jarvis
                    etree.SubElement(root, 'order', {'direction': "descending"}).text = "dateadded"
                    etree.SubElement(root, 'limit').text = limit
                    rule = etree.SubElement(root, 'rule', {'field': "playcount", 'operator': "is"})
                    etree.SubElement(rule, 'value').text = "0"

                elif nodetype == "inprogressepisodes":
                    # Kodi Isengard, Jarvis
                    etree.SubElement(root, 'limit').text = "25"
                    rule = etree.SubElement(root, 'rule',
                        attrib={'field': "inprogress", 'operator':"true"})

            try:
                utils.indent(root)
            except: pass
            etree.ElementTree(root).write(nodeXML)

    def singleNode(self, indexnumber, tagname, mediatype, itemtype):

        tagname = tagname.encode('utf-8')
        cleantagname = utils.normalize_nodes(tagname)
        nodepath = xbmc.translatePath("special://profile/library/video/").decode('utf-8')
        nodeXML = "%splex_%s.xml" % (nodepath, cleantagname)
        path = "library://video/plex%s.xml" % (cleantagname)
        windowpath = "ActivateWindow(Video,%s,return)" % path
        
        # Create the video node directory
        if not xbmcvfs.exists(nodepath):
            # We need to copy over the default items
            shutil.copytree(
                src=xbmc.translatePath("special://xbmc/system/library/video").decode('utf-8'),
                dst=xbmc.translatePath("special://profile/library/video").decode('utf-8'))
            xbmcvfs.exists(path)

        labels = {

            'Favorite movies': 30180,
            'Favorite tvshows': 30181,
            'channels': 30173
        }
        label = utils.language(labels[tagname])
        embynode = "Emby.nodes.%s" % indexnumber
        utils.window('%s.title' % embynode, value=label)
        utils.window('%s.path' % embynode, value=windowpath)
        utils.window('%s.content' % embynode, value=path)
        utils.window('%s.type' % embynode, value=itemtype)

        if xbmcvfs.exists(nodeXML):
            # Don't recreate xml if already exists
            return

        if itemtype == "channels":
            root = self.commonRoot(order=1, label=label, tagname=tagname, roottype=2)
            etree.SubElement(root, 'path').text = "plugin://plugin.video.plexkodiconnect/?id=0&mode=channels"
        else:
            root = self.commonRoot(order=1, label=label, tagname=tagname)
            etree.SubElement(root, 'order', {'direction': "ascending"}).text = "sorttitle"

        etree.SubElement(root, 'content').text = mediatype

        try:
            utils.indent(root)
        except: pass
        etree.ElementTree(root).write(nodeXML)

    def clearProperties(self):

        self.logMsg("Clearing nodes properties.", 1)
        embyprops = utils.window('Emby.nodes.total')
        propnames = [
        
            "index","path","title","content",
            "inprogress.content","inprogress.title",
            "inprogress.content","inprogress.path",
            "nextepisodes.title","nextepisodes.content",
            "nextepisodes.path","unwatched.title",
            "unwatched.content","unwatched.path",
            "recent.title","recent.content","recent.path",
            "recentepisodes.title","recentepisodes.content",
            "recentepisodes.path","inprogressepisodes.title",
            "inprogressepisodes.content","inprogressepisodes.path"
        ]

        if embyprops:
            totalnodes = int(embyprops)
            for i in range(totalnodes):
                for prop in propnames:
                    utils.window('Emby.nodes.%s.%s' % (str(i), prop), clear=True)