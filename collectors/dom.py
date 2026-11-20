"""Small, read-only HTML tree. Source markup is never rendered or executed."""

from html.parser import HTMLParser
import re


class Element:
    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def walk(self):
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.walk()

    def text(self):
        return " ".join(self._text().split())

    def _text(self):
        if self.tag in {"script", "style", "template", "noscript", "svg"}:
            return ""
        return " ".join(x if isinstance(x, str) else x._text() for x in self.children)

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()

    def first_text(self, class_name):
        return next((x.text() for x in self.walk() if x.has_class(class_name)), "")


class Tree(HTMLParser):
    VOID = set(
        "area base br col embed hr img input link meta param source track wbr".split()
    )

    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(markup)
        self.close()

    def handle_starttag(self, tag, attrs):
        if len(self.stack) > 120:
            raise ValueError("Source HTML exceeds permitted nesting")
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, text):
        self.stack[-1].children.append(text)
