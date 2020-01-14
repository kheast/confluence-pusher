
import os
import re
import sys
import subprocess

from subprocess import Popen, PIPE, STDOUT
from atlassian import Confluence

from progress.bar import IncrementalBar as Bar

CONFLUENCE_FILTER_NAME = 'confluence.lua'
CONFLUENCE_FILTER_URL = \
    "https://raw.githubusercontent.com/jpbarrette/pandoc-confluence-writer/master/" + \
    CONFLUENCE_FILTER_NAME
UPDATE_CONFLUENCE_FILTER = "wget " + \
    CONFLUENCE_FILTER_URL + " -O " + CONFLUENCE_FILTER_NAME

CONFLUENCE_FILE_EXTENSION = '.cf'
TMP_FILE = "_filetemp.tmp"

MD_EXTENSION = '.md'
MD_HEADER_START = '# '

IMG_TAG_START = '<ac:image><ri:attachment ri:filename="'
IMG_TAG_END = '" /></ac:image>'

GITBOOK_TAB_BEGIN = '{% tab'
GITBOOK_TAB_END = '%}'
GITBOOK_TABS_END = 'tabs %}'

SVG_EXTENSION = ".svg"
SVG_W_START = 'width="'
SVG_W_END = 'px"'
SVG_H_START = 'height="'
SVG_H_END = 'px"'
SVG_VIEWBOX_TAG = 'viewBox="'

SVG_MAX_WIDTH = 1000
SVG_MAX_HEIGHT = 1500

CONFLUENCE_TAG_AC_STYLE_BEGIN = '<ac:structured-macro ac:macro-id="'
CONFLUENCE_TAG_AC_STYLE_END = '</style>]]></ac:plain-text-body></ac:structured-macro>'
CONFLUENCE_TAG_AC_DIV_BEGIN = '<ac:structured-macro ac:macro-id='
CONFLUENCE_TAG_AC_DIV_END = '</ac:structured-macro>'
CONFLUENCE_TAG_AC_IMAGE_BEGIN = '<ac:image>'
CONFLUENCE_TAG_AC_IMAGE_END = '</ac:image>'
CONFLUENCE_TAG_AC_IMAGE_BEGIN_WIDTH_1000 = \
    '<ac:image ac:align="center" ac:width="' + str(SVG_MAX_WIDTH) + '">'

SOURCE_FOLDER = "./engineering-standards"
CONFLUENCE_SPACE = '~613673678'
CONFLUENCE_URL = 'https://vibrato.atlassian.net'
CONFLUENCE_USERID = 'konstantin.vanyushov@servian.com'
CONFLUENCE_OATOKEN = 'ozL4ruBp6vyjIKpj14la749B'
CONFLUENCE_ROOT_PAGE_NAME = SOURCE_FOLDER.replace('./', '')
CONFLUENCE_SECTION_CONTENT_FILE = "README.md"
CONFLUENCE_TABLE_OF_CONTENTS = "SUMMARY.md"

confluence = Confluence(
    url=CONFLUENCE_URL,
    username=CONFLUENCE_USERID,
    password=CONFLUENCE_OATOKEN)

root_page_id = ''
confluence_parent_id_index = ''
sections = []


def main():

    try:
        update_confluence_filter()
        # Think twice before using this as it will delete the main document
        # tree and all the contents!
        delete_root_page()
        create_root_page()
        convert_files_and_create_confluence_document_tree()
        publish_content_to_confluence()
    # except KeyError:
    #     print("Stopped.")
    # except OSError as err:
    #     print("OS error: {0}".format(err))
    #     raise
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise
    # finally:


def update_confluence_filter():
    os.system(UPDATE_CONFLUENCE_FILTER)


def delete_root_page():
    global root_page_id
    if confluence.page_exists(CONFLUENCE_SPACE, CONFLUENCE_ROOT_PAGE_NAME):
        print('### Deleting root page of the document ###')
        root_page_id = get_confluence_page_id(CONFLUENCE_ROOT_PAGE_NAME)
        confluence.remove_page(
            root_page_id,
            status=None,
            recursive=True)


def create_root_page():
    global root_page_id
    print('### Creating root page of the document ###')
    create_empty_confluence_page(CONFLUENCE_ROOT_PAGE_NAME)
    root_page_id = get_confluence_page_id(CONFLUENCE_ROOT_PAGE_NAME)


def get_confluence_page_id(title):
    return(confluence.get_page_id(
        space=CONFLUENCE_SPACE,
        title=title))


def create_empty_confluence_page(title):
    return(confluence.create_page(
        space=CONFLUENCE_SPACE,
        title=title,
        body=""))


def update_empty_confluence_page(name, parent_id):
    return (confluence.update_or_create(
        parent_id=parent_id,
        title=name,
        body='',
        representation="storage"))


def convert_files_and_create_confluence_document_tree():

    global confluence_parent_id_index
    global root_page_id
    global sections

    md_files_list = []
    confluence_index = []

    for root_folder, dirs, files in os.walk(SOURCE_FOLDER):
        for file in files:
            if file.endswith(MD_EXTENSION) and file != CONFLUENCE_TABLE_OF_CONTENTS:
                md_file_entry = root_folder + '/' + file
                md_files_list.append(md_file_entry)

    progress_bar = Bar(
        'Creating confluence directory tree', max=len(md_files_list))

    for md_file in md_files_list:

        md_file = md_file.replace('\n', '')

        if md_file.endswith(CONFLUENCE_TABLE_OF_CONTENTS) is not True:

            filesystem_path_items = (md_file.replace(
                './', '').replace(MD_EXTENSION, '').split('/'))

            path_index = 0
            for filesystem_item in filesystem_path_items:

                if path_index == 0:
                    parent_id = CONFLUENCE_SPACE
                    title = CONFLUENCE_ROOT_PAGE_NAME
                    page_id = root_page_id
                else:
                    title = filesystem_item

                if path_index == 1:
                    parent_id = root_page_id
                if path_index > 1:
                    parent_id = page_id
                if path_index > 0:
                    if md_file.endswith(CONFLUENCE_SECTION_CONTENT_FILE) is False:
                        status = update_empty_confluence_page(title, parent_id)
                        page_id = get_confluence_page_id(title)

                    confluence_index.append(
                        [md_file, filesystem_item, title, parent_id, page_id])
                path_index += 1
        progress_bar.next()
    progress_bar.finish()
    confluence_parent_id_index = confluence_index


def pandoc_conversion(file_name):
    PANDOC_COMMAND = ['pandoc', '-t',
                      CONFLUENCE_FILTER_NAME, file_name, '--quiet']
    pandoc = subprocess.Popen(PANDOC_COMMAND, stdout=PIPE,
                              stdin=PIPE, stderr=STDOUT)
    confluence_content = pandoc.communicate()
    return(confluence_content[0].decode('UTF-8'))


def find_svg_image_filename(link):
    begin = link.rfind("/") + 1
    return(link[begin:])


def find_svg_image_link(content):
    path = []
    img_tag_begin_positions = [(entry.end()) for entry in list(
        re.finditer(IMG_TAG_START, content))]
    img_tag_end_positions = [(entry.start()) for entry in list(
        re.finditer(IMG_TAG_END, content))]
    index = 0
    for begin in img_tag_begin_positions:
        end = img_tag_end_positions[index]
        img_path = content[begin:end].replace(
            IMG_TAG_START, "")
        if img_path:
            path.append(img_path)
        index += 1
    return(path)


def find_svg_image_dimensions(svg_image_path):

    size = []

    svg_file = open(svg_image_path)
    svg_file_content = svg_file.read()
    svg_file.close()

    width_tag_begin_position = svg_file_content.find(SVG_W_START)
    width_tag_end_position = svg_file_content.find(
        SVG_W_END, width_tag_begin_position)
    width_tag_begin_position += len(SVG_W_START)
    width = svg_file_content[width_tag_begin_position:width_tag_end_position]

    height_tag_begin_position = svg_file_content.find(
        SVG_H_START, width_tag_end_position)
    height_tag_end_position = svg_file_content.find(
        SVG_H_END, height_tag_begin_position)
    height = svg_file_content[(height_tag_begin_position +
                               len(SVG_H_START)):height_tag_end_position]

    size = [int(width), int(height)]
    return(size)


def upload_svg_file_to_confluence_as_an_attachment(
        svg_image_path,
        svg_file_name,
        title,
        page_id,
        width_override,
        height_override,
        svg_size,
        svg_size_new):

    SVG_VIEWBOX_CLOSING_TAG = '" '
    old_svg_viewbox_tag = ''
    new_svg_viewbox_tag = ''

    svg_file = open(svg_image_path)
    svg_file_content = svg_file.read()
    svg_file.close()

    if width_override or height_override:
        old_width = SVG_W_START + str(svg_size[0]) + SVG_W_END
        old_height = SVG_H_START + str(svg_size[1]) + SVG_H_END
        new_width = SVG_W_START + str(svg_size_new[0]) + SVG_W_END
        new_height = SVG_H_START + str(svg_size_new[1]) + SVG_H_END

        if width_override:
            new_height = SVG_H_START + 'auto"'
        if height_override:
            new_width = SVG_W_START + 'auto"'

        svg_file_content = svg_file_content.replace(
            old_width, new_width).replace(old_height, new_height)

        svg_viewbox_start = svg_file_content.find(SVG_VIEWBOX_TAG)
        svg_viewbox_end = svg_file_content.find(
            SVG_VIEWBOX_CLOSING_TAG, (svg_viewbox_start + len(SVG_W_START)))

        old_svg_viewbox_tag = (
            svg_file_content[svg_viewbox_start:svg_viewbox_end]
            + SVG_VIEWBOX_CLOSING_TAG)

        new_svg_viewbox_tag = old_svg_viewbox_tag + \
            ' preserveAspectRatio="none" '

        svg_file_content = svg_file_content.replace(
            old_svg_viewbox_tag, new_svg_viewbox_tag)

    confluence.attach_content(
        content=svg_file_content,
        name=svg_file_name,
        content_type='image',
        page_id=page_id,
        title=title,
        space=None,
        comment=None)


def cleanup_confluence_html(content):
    def content_cleanup(content, begin_tag, end_tag):
        begin = content.find(begin_tag)
        end = content.find(end_tag)
        content = content.replace(
            (content[begin:end] + end_tag), '')
        return (content)
    content = content_cleanup(
        content, CONFLUENCE_TAG_AC_STYLE_BEGIN, CONFLUENCE_TAG_AC_STYLE_END)
    content = content_cleanup(content, GITBOOK_TAB_BEGIN, GITBOOK_TAB_END)
    content = content_cleanup(content, GITBOOK_TAB_BEGIN, GITBOOK_TABS_END)
    return (content)


def find_markdown_title(file):
    title = ''
    for line in file:
        if line.strip().startswith(MD_HEADER_START):
            title = line.replace(MD_HEADER_START, '')
            title = title.replace('\n', '')
    return(title)


def publish_content_to_confluence():
    global confluence_parent_id_index
    global root_page_id

    progress_bar = Bar(
        'Publishing content to Confluence', max=len(confluence_parent_id_index))
    for file_record in confluence_parent_id_index:
        file_path = file_record[0]

        title = file_record[2]
        parent_id = file_record[3]
        page_id = file_record[4]

        if file_path.endswith(CONFLUENCE_SECTION_CONTENT_FILE):
            page_id = parent_id
            parent_name = file_path.replace(
                ('/' + CONFLUENCE_SECTION_CONTENT_FILE), '').split('/')[-2:-1]
            if parent_name == '.':
                parent_id = root_page_id
            else:
                parent_id = get_confluence_page_id(parent_name[0])

        confluence_file_content = pandoc_conversion(file_path)

        svg_images = find_svg_image_link(confluence_file_content)

        for svg_image_path in svg_images:
            confluence_file_content = resize_and_upload_svg_image(
                svg_image_path, confluence_file_content, title, page_id)

        confluence_file_content = cleanup_confluence_html(
            confluence_file_content)

        confluence.update_page(
            page_id=page_id,
            title=title,
            body=confluence_file_content,
            parent_id=parent_id,
            type='page',
            representation='storage',
            minor_edit=False)
        progress_bar.next()
    progress_bar.finish()


def resize_and_upload_svg_image(svg_image_path, confluence_file_content, title, page_id):
    SVG_WIDTH_OVERRIDE = False
    SVG_HEIGHT_OVERRIDE = False

    svg_size_new = []

    if svg_image_path and svg_image_path.endswith(SVG_EXTENSION):
        svg_file_name = find_svg_image_filename(svg_image_path)
        confluence_file_content = confluence_file_content.replace(
            svg_image_path, svg_file_name)
        if svg_image_path.startswith('../../'):
            svg_image_path = svg_image_path.replace(
                '../..', SOURCE_FOLDER)
        else:
            svg_image_path = SOURCE_FOLDER + "/" + \
                svg_image_path.replace('../', '')

        svg_size = find_svg_image_dimensions(svg_image_path)
        if svg_size:
            if int(svg_size[0]) > SVG_MAX_WIDTH and int(svg_size[0]) > int(svg_size[1]):
                SVG_WIDTH_OVERRIDE = True
                svg_aspect_ratio = (svg_size[0] / svg_size[1])
                svg_new_height = int(
                    (SVG_MAX_WIDTH / svg_aspect_ratio))
                svg_size_new = [SVG_MAX_WIDTH, svg_new_height]
            elif int(svg_size[1]) > SVG_MAX_HEIGHT:
                SVG_HEIGHT_OVERRIDE = True
                svg_aspect_ratio = (svg_size[1] / svg_size[0])
                svg_new_height = int(
                    (SVG_MAX_HEIGHT / svg_aspect_ratio))
                svg_size_new = [SVG_MAX_HEIGHT, svg_new_height]

        upload_svg_file_to_confluence_as_an_attachment(
            svg_image_path,
            svg_file_name,
            title, page_id,
            SVG_WIDTH_OVERRIDE,
            SVG_HEIGHT_OVERRIDE,
            svg_size,
            svg_size_new)
    return confluence_file_content


main()
