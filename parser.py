# *.* coding: utf-8 *.*

import os
import shutil
import copy
import re

PROTOTYPE_PATH = "Prototype"
SITE_PATH = "Site"


class TemplateMaker:
    def __init__(self, templates_path):
        self.templates_path = templates_path
        self.templates = {}
        self.get_templates()

    def get_templates(self):
        for root, _, filenames in os.walk(self.templates_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                with open(file_path, "r", encoding="utf-8") as template_file:
                    template = template_file.read()

                template_name = filename.replace(".html", "")
                self.templates[template_name] = template

    def template_keyword(self, template_name):
        """ Return the identifier that should be replaced """
        return '$' + template_name

    def fill_file_templates(self, file_path):
        """ Fill templates in the given file """
        with open(file_path, "r", encoding="utf-8") as page_file:
            page_content = page_file.read()

        for template_name, template_content in self.templates.items():
            keyword = self.template_keyword(template_name)
            page_content = page_content.replace(keyword, template_content)

        with open(file_path, "w", encoding="utf-8") as new_page_file:
            new_page_file.write(page_content)

    def fill_path_templates(self, path):
        """ Fill all templates found in the files under path """
        for root, dirnames, filenames in os.walk(path):
            for filename in filenames:
                extension = filename.split(".")[-1]
                if extension != "html":
                    continue
                else:
                    file_path = os.path.join(root, filename)
                    self.fill_file_templates(file_path)


class Tag:
    def __init__(self, name, properties={}, children=[], class_list=[]):
        self.class_list = copy.copy(class_list)
        self.name = name
        self.children = copy.copy(children)
        self.properties = properties

    def open_tag(self):
        properties = ""
        for name, value in self.properties.items():
            properties += " " + name + "=" + value

        result = "<" + self.name + properties + " class = ' "
        for class_name in self.class_list:
            result += class_name + " "
        result += "'>"
        return result

    def close_tag(self):
        result = "</" + self.name + ">"
        return result

    def append(self, *args):
        for child in args:
            self.children.append(child)

    def __str__(self):
        result = ""
        result += self.open_tag()
        for child in self.children:
            result += str(child) + " "

        result += self.close_tag()
        return result

    def __repr__(self):
        return self.name + " tag"


class ImgTag:
    def __init__(self, src):
        self.src = src

    def __str__(self):
        return f'<img src={self.src}/>'


class PageBuilder:
    SECTION_SEPARATOR = '---'
    CODE_SEPARATOR = '```'
    SECTION_TITLE_MARKER = '#'
    NOTE_MARKER = '|'
    MONOSPACE_SEPARATOR = '`'

    def __init__(self):
        self.table_of_contents = []

    def build_pages(self, pages_path, target_path):
        """ Build all pages in the directory and put them to the target """
        for root, dirnames, filenames in os.walk(pages_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                target_filename = filename.split('.')[0] + '.html'
                target_path = os.path.join(target_path, target_filename)
                self.build_page(file_path, target_path)

    def build_page(self, page_path, target_path):
        """ Create a HTML file in the target path 
            basing on the given file path
        """
        with open(page_path, "r", encoding="utf-8") as page_file:
            page_content = page_file.read()

        new_page_content = self.build_html(page_content, page_path)

        with open(target_path, "w", encoding="utf-8") as new_page_file:
            new_page_file.write(new_page_content)

    def build_html(self, page_content, page_path):
        """ Return the HTML string made of given text """

        sections = page_content.split(PageBuilder.SECTION_SEPARATOR)

        page_data = self.extract_page_data(sections[0])
        page_data['path'] = page_path.split('\\')[-1].replace('txt', 'html')
        self.table_of_contents.append(page_data)

        html = Tag('html')
        head = Tag('head', children=["$head"])

        head.append(Tag('title', children=[page_data['title']]))
        body = Tag('body', children=["$menu"])
        container = Tag('div', class_list=['container'])
        body.append(container)

        header = True
        for section_content in sections:
            container.append(self.build_section(
                section_content, header=header))
            header = False

        html.append(head, body)
        return '<!DOCTYPE html>\n' + str(html)

    def extract_page_data(self, header):
        page_data = {}
        data_names = ['category', 'category_id', 'title']
        for line in header.split('\n'):
            for data_name in data_names:
                if data_name + ':' in line:
                    value = line.split(data_name + ':')[1]
                    page_data[data_name] = value.strip()

        return page_data

    def build_section(self, section_content, header=False):
        """ Creates a Tag object representing section """
        print("Building section")

        section = Tag('section')
        if header:
            section.class_list.append('header')

        lines = section_content.split('\n')

        note = ''
        quote = ''
        code = ''
        code_open = False
        ignore_if_find = ['category:', 'category_id:']
    
        for line in lines:
            if code_open and line != PageBuilder.CODE_SEPARATOR:
                code += line + '\n'

            ignore_line = False
            for ignored in ignore_if_find:
                if ignored in line:
                    ignore_line = True
                
            if ignore_line:
                continue

            if len(line) == 0:
                if note != "":
                    note_tag = Tag('div', children=[note], class_list=['note'])
                    section.append(note_tag)
                    note = ''
        
            elif "title:" in line:
                title = line.split("title:")[1]
                section.append(Tag('h2', children=[title],
                                   class_list=['title']))

            elif line[0] == PageBuilder.SECTION_TITLE_MARKER:
                section.append(Tag('h6', children=[line[1:]],
                                   class_list=['section-title']))

            elif line[0] == PageBuilder.NOTE_MARKER:
                note += line[1:] + '<br>'

            elif PageBuilder.CODE_SEPARATOR in line:
                if code != "":
                    pre_tag = Tag("pre", class_list=['code-example'])
                    code_tag = Tag("code", children=[code],
                                   class_list=['code-example-body', 'cpp'])
                    pre_tag.append(code_tag)
                    section.append(pre_tag)
                    code_open = False
                else:
                    code_open = True

            elif line[:3] == 'img':
                pattern = re.compile(r'img\((.*)\)')
                src = pattern.match(line).group(1)
                img_wrapper = Tag('div',
                                  children=[ImgTag(src)],
                                  class_list=['img-wrapper'])
                section.append(img_wrapper)

            elif line[:4] == 'href':
                pattern = re.compile(r'href\((.*)\)\[(.*)\]')
                link_text = pattern.match(line).group(1)
                link_href = pattern.match(line).group(2)
                link = Tag('a', 
                    properties={'href': link_href},
                    children=[link_text])
                section.append(link)

            else:
                if '`' in line:
                    pattern = re.compile(r'.*`(.*)`.*')
                    code_content = pattern.match(line).group(1)
                    code = Tag('code', children=[code_content])

                    line = line.split('`' + code_content + '`')
                    section.append(line[0], code, line[1])

                else:
                    section.append(line)

        return section


    def build_table_of_contents(self, path):
        categories = {}
        category_ids = {}

        for data in self.table_of_contents:
            category = data['category']
            if category not in categories:
                categories[category] = []
            category_ids[category] = data['category_id']
            categories[category].append(data)

        section = Tag('section')
        ul = Tag('ul', class_list=['table-of-contents'])
        section.append(ul)

        for category in categories:
            category_item = Tag('li')
            category_header = Tag('span', 
                children=[category],
                properties={'id': category_ids[category]},
                class_list=['list-header'])
            category_item.append(category_header)

            category_list = Tag('ul')
            for page_data in categories[category]:
                page_item = Tag('li')
                page_link = Tag('a',
                    properties={'href': page_data['path']},
                    children=[page_data['title']])
                page_item.append(page_link)
                category_list.append(page_item)

            category_item.append(category_list)
            ul.append(category_item)

        table_of_contents = str(section)
        with open(path, 'w') as table_of_contents_file:
            table_of_contents_file.write(table_of_contents)

def prepare_directory(path):
    try:
        shutil.rmtree(path)
    except Exception as e:
        print(e)

    os.makedirs(path)


def copy_prototype(path_from, path_to):
    ignore = ["_prototype"]
    for tree in os.listdir(path_from):
        if tree in ignore:
            continue
        try:
            shutil.copytree(os.path.join(path_from, tree),
                            os.path.join(path_to, tree))
        except:
            shutil.copy(os.path.join(path_from, tree),
                        os.path.join(path_to, tree))

        print("Copying tree:", tree)


def build_prototype():
    prepare_directory("Site")

    page_builder = PageBuilder()
    page_builder.build_pages("Prototype\\_prototype\\pages", "Site")
    page_builder.build_table_of_contents("Prototype\\_prototype\\templates\\table_of_contents.html")

    copy_prototype("Prototype", "Site")

    template_maker = TemplateMaker("Prototype\\_prototype\\templates")
    template_maker.fill_path_templates("Site")


build_prototype()
