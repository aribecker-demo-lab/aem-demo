"""Build the FileVault content package from the pinned WKND release."""
import argparse
import io
import re
from html import escape
from pathlib import Path
from xml.dom import minidom
from zipfile import ZIP_DEFLATED, ZipFile

SAMPLE_PACKAGE = (
    "jcr_root/apps/wknd-packages/content/install/"
    "aem-guides-wknd.ui.content.sample-4.0.4.zip"
)
ADVENTURES = "/content/wknd/us/en/adventures"
SOURCE = f"{ADVENTURES}/bali-surf-camp"
TARGET = f"{ADVENTURES}/bali-surf-camp-demo"
SECTION_TARGET = f"{ADVENTURES.rsplit('/', 1)[0]}/aem-demo"
SECTION_IMAGE = "/content/dam/wknd-demo-components.jpg"
CATALOG_ASSETS = "/content/dam/wknd-demo-catalog"
# slug, title, panel ID, description, image alt text, Pexels photo ID
CATALOG_PAGES = (
    ("core-v2", "Core Components v2", "core-v2-components-frame",
     "Explore the version 2 Core Components installed in this AEM SDK.",
     "Laptop with code on the screen", "1181671"),
    ("core-v3", "Core Components v3", "core-v3-components-frame",
     "Explore the version 3 Core Components installed in this AEM SDK.",
     "Close-up of a screen showing programming code", "34803966"),
    ("wknd-components", "WKND Components", "demo-components-frame",
     "Explore the WKND proxies and custom components.",
     "Web design materials on a desk", "196644"),
    ("weather", "Weather", "weather-components-frame",
     "Check current temperature, humidity and wind in Bali.",
     "Clouds across the sky", "531756"),
)
TEMPLATE_SOURCE = "/conf/wknd/settings/wcm/templates/adventure-page-template"
TEMPLATE_TARGET = f"{TEMPLATE_SOURCE}-demo"
POLICY_ROOT = "/conf/wknd/settings/wcm/policies"
ORIGINAL_CONTAINER_POLICY = "wknd/components/container/policy_213106331986985"
DEMO_CONTAINER_POLICY = "wknd/components/container/adventure-demo"
WEATHER_COMPONENT = "/apps/wknd-demo/components/weather"
DEMO_CLIENTLIB = "/apps/wknd/clientlibs/clientlib-demo-components"

FILTER = f"""<?xml version="1.0" encoding="UTF-8"?>
<workspaceFilter version="1.0">
    <filter root="{TARGET}" mode="replace"/>
    <filter root="{SECTION_TARGET}" mode="replace"/>
    <filter root="{SECTION_IMAGE}" mode="replace"/>
    <filter root="{CATALOG_ASSETS}" mode="replace"/>
    <filter root="{TEMPLATE_TARGET}" mode="replace"/>
    <filter root="{POLICY_ROOT}/{DEMO_CONTAINER_POLICY}" mode="replace"/>
    <filter root="{WEATHER_COMPONENT}" mode="replace"/>
    <filter root="{DEMO_CLIENTLIB}" mode="replace"/>
</workspaceFilter>
"""

PROPERTIES = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
    <entry key="group">wknd-demo</entry>
    <entry key="name">wknd-demo-adventure</entry>
    <entry key="version">1.0.0</entry>
    <entry key="packageType">mixed</entry>
    <entry key="dependencies">com.adobe.aem.guides:aem-guides-wknd.ui.content.sample:4.0.4</entry>
</properties>
"""

DEMO_CLIENTLIB_DEFINITION = """<?xml version="1.0" encoding="UTF-8"?>
<jcr:root xmlns:jcr="http://www.jcp.org/jcr/1.0"
    jcr:primaryType="cq:ClientLibraryFolder"
    categories="[wknd.site]"
    allowProxy="{Boolean}true"/>
"""

DEMO_COMPONENTS_CSS = """[id$="-components-frame"] {
    box-sizing: border-box;
    border: 6px solid #f00;
    padding: clamp(1rem, 3vw, 2rem);
    margin-block: 2rem;
}

#core-v2-components-frame { border-color: #7625a5; }
#core-v3-components-frame { border-color: #1555a3; }
#weather-components-frame { border-color: #db6714; }

#demo-catalog-detail [id$="-components-frame"],
#demo-catalog-detail [id^="demo-preview-"] {
    border: 0;
    padding: 0;
}


.wknd-demo-weather__temperature {
    color: #98420a;
    font-size: clamp(2rem, 6vw, 3rem);
    font-weight: 700;
    margin: 0;
}

.wknd-demo-weather__condition { text-transform: capitalize; }

.wknd-demo-weather__details {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem 2rem;
}

.wknd-demo-weather__details dd { margin: 0; font-weight: 700; }
.wknd-demo-weather__source { font-size: .875rem; }

[id$="-components-frame"] [id^="demo-preview-"] {
    box-sizing: border-box;
    border: 6px solid #16803c;
    min-width: 0;
    padding: clamp(.75rem, 2vw, 1.5rem);
    margin-block: .75rem;
}

#demo-components-frame #demo-components .cmp-title__text,
[id$="-components-frame"] [id^="demo-label-"] h3 {
    color: #005d73;
    font-size: clamp(1.25rem, 2vw, 1.6rem);
    font-weight: 700;
    margin: 0 0 .35rem;
}

[id$="-components-frame"] [id^="demo-meta-"] p {
    color: #343a40;
    margin: 0 0 1rem;
    overflow-wrap: anywhere;
}

[id$="-components-frame"] .cmp-separator__horizontal-rule {
    border: 0;
    border-top: 1px solid #879097;
    margin-block: 1.5rem;
}
"""


# Titles, descriptions, and immediate supertypes from WKND 4.0.4 and the pinned AEM SDK.
COMPONENT_METADATA = {
    "accordion": (
        "Accordion",
        None,
        "core/wcm/components/accordion/v1/accordion",
        "Accordion (v1)",
        "Displays content as an accordion",
    ),
    "breadcrumb": (
        "Breadcrumb",
        None,
        "core/wcm/components/breadcrumb/v3/breadcrumb",
        "Breadcrumb (v3)",
        "Displays the position of the current page within the site hierarchy",
    ),
    "button": (
        "Button",
        None,
        "core/wcm/components/button/v2/button",
        "Button (v2)",
        "Button",
    ),
    "byline": (
        "Byline",
        "Displays a contributor's byline.",
        "core/wcm/components/image/v3/image",
        "Image (v3)",
        "Smart Adaptive Image",
    ),
    "carousel": (
        "Carousel",
        None,
        "core/wcm/components/carousel/v1/carousel",
        "Carousel (v1)",
        "Cycles through a list of generic content items",
    ),
    "container": (
        "Container",
        None,
        "core/wcm/components/container/v1/container",
        "Container (v1)",
        "Container component, used to group other components and apply a common style or layout.",
    ),
    "contentfragment": (
        "Content Fragment",
        None,
        "core/wcm/components/contentfragment/v1/contentfragment",
        "Content Fragment (v1)",
        "Displays the elements of a Content Fragment or a selection thereof",
    ),
    "contentfragmentlist": (
        "Content Fragment List",
        None,
        "core/wcm/components/contentfragmentlist/v2/contentfragmentlist",
        "Content Fragment List (v2)",
        "Displays a list of Content Fragments",
    ),
    "download": (
        "Download",
        None,
        "core/wcm/components/download/v2/download",
        "Download (v2)",
        "Displays a downloadable DAM asset with optional title, description, metadata and action text.",
    ),
    "embed": (
        "Embed",
        None,
        "core/wcm/components/embed/v2/embed",
        "Embed (v2)",
        "Embed a third-party widget or safe free-form HTML.",
    ),
    "experiencefragment": (
        "Experience Fragment",
        None,
        "core/wcm/components/experiencefragment/v2/experiencefragment",
        "Experience Fragment (v2)",
        "Displays an experience fragment variation",
    ),
    "helloworld": (
        "Hello World Component",
        None,
        None,
        None,
        None,
    ),
    "image": (
        "Image",
        None,
        "core/wcm/components/image/v3/image",
        "Image (v3)",
        "Smart Adaptive Image",
    ),
    "image-list": (
        "Image List",
        None,
        "core/wcm/components/list/v3/list",
        "List (v3)",
        "Configurable collection of items or content",
    ),
    "list": (
        "List",
        None,
        "core/wcm/components/list/v3/list",
        "List (v3)",
        "Configurable collection of items or content",
    ),
    "separator": (
        "Separator",
        None,
        "core/wcm/components/separator/v1/separator",
        "Separator (v1)",
        "Displays a horizontal rule for separating content",
    ),
    "sharing": (
        "Social Media Sharing",
        None,
        "core/wcm/components/sharing/v1/sharing",
        "Social Media Sharing (v1)",
        "Core WCM Social Media Sharing Component (v1)",
    ),
    "tabs": (
        "Tabs",
        None,
        "core/wcm/components/tabs/v1/tabs",
        "Tabs (v1)",
        "Displays content as a list of tabs",
    ),
    "teaser": (
        "Teaser",
        None,
        "core/wcm/components/teaser/v2/teaser",
        "Teaser (v2)",
        "Teaser block allowing a combination of an image, title, rich text description and actions/links",
    ),
    "text": (
        "Text",
        None,
        "core/wcm/components/text/v2/text",
        "Text (v2)",
        "Rich Text Section",
    ),
    "title": (
        "Title",
        None,
        "core/wcm/components/title/v3/title",
        "Title (v3)",
        "Section Heading",
    ),
}


# Authorable v2/v3 definitions present in the pinned AEM Cloud SDK.
CORE_COMPONENTS = (
    (
        "core/wcm/components/breadcrumb/v2/breadcrumb",
        "Breadcrumb (v2)",
        "Displays the position of the current page within the site hierarchy",
    ),
    (
        "core/wcm/components/breadcrumb/v3/breadcrumb",
        "Breadcrumb (v3)",
        "Displays the position of the current page within the site hierarchy",
    ),
    (
        "core/wcm/components/button/v2/button",
        "Button (v2)",
        "Button",
    ),
    (
        "core/wcm/components/contentfragmentlist/v2/contentfragmentlist",
        "Content Fragment List (v2)",
        "Displays a list of Content Fragments",
    ),
    (
        "core/wcm/components/form/container/v2/container",
        "Core Form Container (v2)",
        "Container allowing to construct simple forms for visitors to submit information",
    ),
    (
        "core/wcm/components/download/v2/download",
        "Download (v2)",
        "Displays a downloadable DAM asset with optional title, description, metadata and action text.",
    ),
    (
        "core/wcm/components/embed/v2/embed",
        "Embed (v2)",
        "Embed a third-party widget or safe free-form HTML.",
    ),
    (
        "core/wcm/components/experiencefragment/v2/experiencefragment",
        "Experience Fragment (v2)",
        "Displays an experience fragment variation",
    ),
    (
        "core/wcm/components/form/button/v2/button",
        "Form Button (v2)",
        "Allows visitors to interact with the form",
    ),
    (
        "core/wcm/components/form/hidden/v2/hidden",
        "Form Hidden (v2)",
        "Allows form owner to add hidden data to the form",
    ),
    (
        "core/wcm/components/form/options/v2/options",
        "Form Options (v2)",
        "Allows visitors to select available options",
    ),
    (
        "core/wcm/components/form/text/v2/text",
        "Form Text (v2)",
        "Allows visitors to enter text information",
    ),
    (
        "core/wcm/components/image/v2/image",
        "Image (v2)",
        "Smart Adaptive Image",
    ),
    (
        "core/wcm/components/image/v3/image",
        "Image (v3)",
        "Smart Adaptive Image",
    ),
    (
        "core/wcm/components/languagenavigation/v2/languagenavigation",
        "Language Navigation (v2)",
        "Global language structure navigation",
    ),
    (
        "core/wcm/components/list/v2/list",
        "List (v2)",
        "Configurable collection of items or content",
    ),
    (
        "core/wcm/components/list/v3/list",
        "List (v3)",
        "Configurable collection of items or content",
    ),
    (
        "core/wcm/components/navigation/v2/navigation",
        "Navigation (v2)",
        "Collects a list of pages to display in a navigation tree.",
    ),
    (
        "core/wcm/components/teaser/v2/teaser",
        "Teaser (v2)",
        "Teaser block allowing a combination of an image, title, rich text description and actions/links",
    ),
    (
        "core/wcm/components/text/v2/text",
        "Text (v2)",
        "Rich Text Section",
    ),
    (
        "core/wcm/components/title/v2/title",
        "Title (v2)",
        "Section Heading",
    ),
    (
        "core/wcm/components/title/v3/title",
        "Title (v3)",
        "Section Heading",
    ),
)

def add_demo_components(document: minidom.Document) -> None:
    """Insert examples in the editable body before the existing adventure."""
    root = document.getElementsByTagName("root")[0]
    body = next(
        node for node in root.childNodes
        if node.nodeType == node.ELEMENT_NODE and node.tagName == "container"
    )
    first = body.firstChild

    def component(node_name, component_type, **properties):
        node = document.createElement(node_name)
        node.setAttribute("jcr:primaryType", "nt:unstructured")
        node.setAttribute("sling:resourceType", component_type if "/" in component_type
                          else f"wknd/components/{component_type}")
        for key, value in properties.items():
            node.setAttribute(key, value)
        return node

    assets = "/content/dam/wknd-shared/en/adventures/bali-surf-camp"
    image = f"{assets}/adobestock-175749320.jpg"
    fragment = f"{assets}/bali-surf-camp"
    lists = dict(listFrom="children", parentPage=ADVENTURES,
                 childDepth="{Long}1", maxItems="{Long}3",
                 orderBy="title", sortOrder="asc")

    container = component("demo_container", "container", layout="responsiveGrid")
    container.appendChild(component("text", "text", text="<p>Container example.</p>",
                                    textIsRich="{Boolean}true"))
    accordion = component("demo_accordion", "accordion")
    accordion.appendChild(component("text", "text", text="<p>Accordion panel example.</p>",
                                    textIsRich="{Boolean}true",
                                    **{"cq:panelTitle": "Accordion example"}))
    tabs = component("demo_tabs", "tabs")
    tabs.appendChild(component("text", "text", text="<p>Tabs panel example.</p>",
                               textIsRich="{Boolean}true",
                               **{"cq:panelTitle": "Example tab"}))
    carousel = component("demo_carousel", "carousel")
    carousel.appendChild(component("image", "image", fileReference=image,
                                   alt="Surfer in Bali"))
    carousel.appendChild(component(
        "image_2", "image", alt="Surf camp",
        fileReference=(
            "/content/dam/wknd-shared/en/adventures/surf-camp-in-costa-rica/"
            "adobestock-266405335.jpeg"
        ),
    ))

    examples = [
        component("demo_separator_start", "separator"),
        component("demo_title", "title", type="h2",
                  **{"jcr:title": "Demo Components", "id": "demo-components"}),
        component("demo_text", "text",
                  text="<h3>Text Component Example for Bali Surf Camp</h3>",
                  textIsRich="{Boolean}true", id="demo-label-text"),
        component("demo_button", "button", link=SOURCE, **{"jcr:title": "View Bali Surf Camp"}),
        component("demo_download", "download", fileReference=image,
                  **{"jcr:title": "Download the surf camp photo", "actionText": "Download photo"}),
        component("demo_sharing", "sharing"),
        component("demo_image", "image", fileReference=image, alt="Surfer in Bali"),
        component("demo_teaser", "teaser", fileReference=image, linkURL=SOURCE,
                  titleFromPage="{Boolean}false", descriptionFromPage="{Boolean}false",
                  **{"jcr:title": "Bali Surf Camp Teaser",
                     "jcr:description": "<p>Explore the original adventure.</p>"}),
        carousel,
        component("demo_embed", "embed", type="html", html="<p>Embed HTML example.</p>"),
        container,
        component("demo_separator_example", "separator"),
        accordion,
        tabs,
        component("demo_list", "list", **lists),
        component("demo_breadcrumb", "breadcrumb", startLevel="{Long}4",
                  hideCurrent="{Boolean}false"),
        component("demo_content_fragment", "contentfragment", fragmentPath=fragment,
                  elementNames="description", variationName="master", displayMode="multi"),
        component("demo_content_fragment_list", "contentfragmentlist",
                  modelPath="/conf/wknd-shared/settings/dam/cfm/models/adventure",
                  parentPath=assets, elementNames="[title,description]", maxItems="{Long}1"),
        component("demo_experience_fragment", "experiencefragment",
                  fragmentVariationPath=(
                      "/content/experience-fragments/wknd/us/en/adventures/bali-surf-camp/card"
                  )),
        component("demo_byline", "byline", name="WKND Demo",
                  occupations="[Adventure editor]", fileReference=image),
        component("demo_image_list", "image-list", **lists),
        component("demo_hello_world", "helloworld", text="Hello from Bali Surf Camp."),
        component("demo_separator_end", "separator"),
    ]
    frame = component("demo_components_frame", "container", id="demo-components-frame")
    frame.appendChild(examples[0])
    for example in examples[1:-1]:
        resource_type = example.getAttribute("sling:resourceType")
        component_type = resource_type.rsplit("/", 1)[-1]
        name = example.tagName
        title, description, supertype, super_title, super_description = COMPONENT_METADATA[
            component_type
        ]
        label = component_type not in {"text", "title"}
        if label:
            frame.appendChild(component(
                f"{name}_label", "text", id=f"demo-label-{component_type}",
                text=f"<h3>{escape(title)}</h3>", textIsRich="{Boolean}true",
            ))
        if component_type == "image-list":
            description = "WKND list that presents pages as cards with images."
        elif component_type == "helloworld":
            description = "Example component that displays authored text and a Sling Model message."
        elif description is None:
            description = "WKND proxy. See the description of the supertype."

        details = (
            f"<p><strong>Component title</strong> {escape(title)}<br>"
            f"<strong>Resource Type is</strong> <code>{escape(resource_type)}</code><br>"
            f"<strong>Component description</strong> {escape(description)}</p>"
        )
        if supertype:
            details += (
                f"<p><strong>Supertype title</strong> {escape(super_title)}<br>"
                f"<strong>Supertype Resource Type</strong> <code>{escape(supertype)}</code><br>"
                f"<strong>Supertype description</strong> {escape(super_description)}</p>"
            )
        else:
            details += "<p><strong>Supertype</strong> None defined.</p>"
        metadata = component(
            f"{name}_resource_type", "text", id=f"demo-meta-{component_type}",
            text=details,
            textIsRich="{Boolean}true",
        )
        if label:
            frame.appendChild(metadata)
        preview = component(
            f"{name}_preview", "container", id=f"demo-preview-{component_type}",
        )
        preview.appendChild(example)
        frame.appendChild(preview)
        if not label:
            frame.appendChild(metadata)
        frame.appendChild(component(f"{name}_divider", "separator"))
    body.insertBefore(frame, first)

    examples_by_type = {
        node.getAttribute("sling:resourceType").rsplit("/", 1)[-1]: node
        for node in examples[1:-1]
    }
    for version in ("v2", "v3"):
        panel = component(f"core_{version}_components", "container",
                          id=f"core-{version}-components-frame")
        panel.appendChild(component(
            "heading", "title", type="h2",
            **{"jcr:title": f"Core Components {version}"},
        ))
        panel.appendChild(component("heading_divider", "separator"))
        form = None
        for resource_type, title, description in CORE_COMPONENTS:
            if f"/{version}/" not in resource_type:
                continue
            is_form = "/form/" in resource_type
            kind = resource_type.rsplit("/", 1)[-1]
            name = f"form_{kind}" if is_form else kind
            label = component(
                f"{name}_label", "text", id=f"demo-label-core-{version}-{name}",
                text=(f"<h3>{escape(title)}</h3><p><strong>Resource Type is</strong> "
                      f"<code>{escape(resource_type)}</code><br>{escape(description)}</p>"),
                textIsRich="{Boolean}true",
            )
            if is_form:
                settings = {
                    "text": {"name": "demoText", "type": "text"},
                    "options": {"name": "demoOption", "type": "radio",
                                "source": "local"},
                    "hidden": {"name": "demoHidden", "value": "WKND"},
                    "button": {"name": "demoReset", "type": "reset"},
                    "container": {},
                }[kind]
                example = component(name, resource_type, **{"jcr:title": title, **settings})
                if kind == "options":
                    option = document.createElement("items")
                    option.setAttribute("jcr:primaryType", "nt:unstructured")
                    item = document.createElement("item0")
                    item.setAttribute("jcr:primaryType", "nt:unstructured")
                    item.setAttribute("text", "Bali Surf Camp")
                    item.setAttribute("value", "bali")
                    option.appendChild(item)
                    example.appendChild(option)
                if kind != "container":
                    form.appendChild(label)
                    form.appendChild(example)
                    form.appendChild(component(f"{name}_divider", "separator"))
                    continue
                form = example
            elif kind in examples_by_type:
                example = examples_by_type[kind].cloneNode(deep=True)
                document.renameNode(example, None, name)
                example.setAttribute("sling:resourceType", resource_type)
                if example.hasAttribute("id"):
                    example.removeAttribute("id")
                if kind == "title":
                    example.setAttribute("jcr:title", "Bali Surf Camp")
                elif kind == "text":
                    example.setAttribute("text", "<p>Explore the Bali Surf Camp adventure.</p>")
            else:
                example = component(
                    name, resource_type, navigationRoot="/content/wknd" if kind == "languagenavigation"
                    else "/content/wknd/us/en", structureDepth="{Long}2",
                    skipNavigationRoot="{Boolean}true",
                )
            panel.appendChild(label)
            preview = component(f"{name}_preview", "container",
                                id=f"demo-preview-core-{version}-{name}")
            preview.appendChild(example)
            panel.appendChild(preview)
            panel.appendChild(component(f"{name}_divider", "separator"))
        body.insertBefore(panel, first)

    weather_panel = component("weather_panel", "container", id="weather-components-frame")
    weather_panel.appendChild(component(
        "heading", "title", type="h2", **{"jcr:title": "Weekend Content Demo"},
    ))
    weather_panel.appendChild(component("weather", "wknd-demo/components/weather"))
    body.insertBefore(weather_panel, first)


SECTION_IMAGE_DEFINITION = """<?xml version="1.0" encoding="UTF-8"?>
<jcr:root xmlns:jcr="http://www.jcp.org/jcr/1.0"
    xmlns:dam="http://www.day.com/dam/1.0"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    jcr:primaryType="dam:Asset">
    <jcr:content jcr:primaryType="dam:AssetContent" dam:assetState="processed">
        <metadata jcr:primaryType="nt:unstructured" dc:format="image/jpeg"
            dc:title="Illustration of a component library"/>
        <renditions jcr:primaryType="nt:folder"/>
    </jcr:content>
</jcr:root>
"""


def build_section(landing_source: bytes) -> bytes:
    with minidom.parseString(landing_source) as document:
        root = document.documentElement
        page = document.getElementsByTagName("jcr:content")[0]
        for child in list(root.childNodes):
            if child.nodeType == child.ELEMENT_NODE and child is not page:
                root.removeChild(child)
        for node in document.getElementsByTagName("*"):
            for key in ("cq:lastRolledout", "cq:lastRolledoutBy", "jcr:mixinTypes"):
                if node.hasAttribute(key):
                    node.removeAttribute(key)

        page.setAttribute("jcr:title", "AEM Demo")
        page.setAttribute("navTitle", "AEM Demo")
        page.setAttribute("hideInNav", "{Boolean}false")
        page.setAttribute("jcr:description", "Explore the AEM component library.")
        page.removeAttribute("cq:tags")

        teaser = page.getElementsByTagName("teaser")[0]
        teaser.setAttribute("jcr:title", "Explore AEM components")
        teaser.setAttribute("jcr:description", "<p>See WKND and Core Components in action.</p>")
        teaser.setAttribute("fileReference", SECTION_IMAGE)
        teaser.setAttribute("alt", "Laptop displaying a library of website components")
        teaser.setAttribute("altValueFromDAM", "{Boolean}false")
        teaser.removeChild(teaser.getElementsByTagName("actions")[0])

        titles = page.getElementsByTagName("title")
        titles[1].setAttribute("jcr:title", "Component demos")
        tabs = page.getElementsByTagName("tabs")[0]
        for child in list(tabs.childNodes):
            if child.nodeType == child.ELEMENT_NODE and child.getAttribute("cq:panelTitle") != "All":
                tabs.removeChild(child)
        return document.toxml(encoding="UTF-8")


def build_catalog_page(page_source: bytes, item: tuple[str, ...]) -> bytes:
    slug, title, panel_id, description, alt, _ = item
    with minidom.parseString(page_source) as document:
        content = document.getElementsByTagName("jcr:content")[0]
        content.setAttribute("jcr:title", title)
        content.setAttribute("navTitle", title)
        content.setAttribute("jcr:description", description)
        content.setAttribute("hideInNav", "{Boolean}false")
        content.removeAttribute("cq:tags")

        root = content.getElementsByTagName("root")[0]
        body = root.getElementsByTagName("container")[0]
        body.setAttribute("id", "demo-catalog-detail")
        for child in list(body.childNodes):
            if child.nodeType == child.ELEMENT_NODE and child.getAttribute("id") != panel_id:
                body.removeChild(child)

        cover = document.createElement("card_image")
        for key, value in {
            "jcr:primaryType": "nt:unstructured",
            "sling:resourceType": "wknd/components/image",
            "fileReference": f"{CATALOG_ASSETS}/{slug}.jpg",
            "alt": alt,
            "altValueFromDAM": "{Boolean}false",
        }.items():
            cover.setAttribute(key, value)
        # Image List picks the first matching Image resource in path order.
        body.insertBefore(cover, body.firstChild)
        return document.toxml(encoding="UTF-8")


def write_jpeg_asset(package: ZipFile, asset_path: str, image: Path, definition: str) -> None:
    asset = f"jcr_root{asset_path}"
    package.writestr(f"{asset}/.content.xml", definition)
    rendition = f"{asset}/_jcr_content/renditions/original"
    package.write(image, rendition)
    package.writestr(f"{rendition}.dir/.content.xml", """<?xml version="1.0" encoding="UTF-8"?>
<jcr:root xmlns:jcr="http://www.jcp.org/jcr/1.0" jcr:primaryType="nt:file">
    <jcr:content jcr:primaryType="nt:resource" jcr:mimeType="image/jpeg"/>
</jcr:root>
""")


def build_package(
    wknd_release: Path, output: Path, weather_source: Path, section_image: Path,
) -> None:
    with ZipFile(wknd_release) as release:
        sample_bytes = release.read(SAMPLE_PACKAGE)
    with ZipFile(io.BytesIO(sample_bytes)) as sample:
        page = sample.read(f"jcr_root{SOURCE}/.content.xml").decode("utf-8")
        landing_source = sample.read(f"jcr_root{ADVENTURES}/.content.xml")
        source_policies = sample.read(f"jcr_root{POLICY_ROOT}/.content.xml")
        template_prefix = f"jcr_root{TEMPLATE_SOURCE}/"
        template_files = {
            name.removeprefix(template_prefix): sample.read(name)
            for name in sample.namelist()
            if name.startswith(template_prefix) and not name.endswith("/")
        }

    template_files[".content.xml"] = template_files[".content.xml"].replace(
        b'jcr:title="Adventure Page Template"',
        b'jcr:title="Adventure Page Template - Demo"',
        1,
    )
    for name in ("structure/.content.xml", "initial/.content.xml"):
        template_files[name] = template_files[name].replace(
            f'cq:template="{TEMPLATE_SOURCE}"'.encode(),
            f'cq:template="{TEMPLATE_TARGET}"'.encode(),
        )

    with minidom.parseString(source_policies) as policies:
        original = policies.getElementsByTagName(ORIGINAL_CONTAINER_POLICY.rsplit("/", 1)[1])[0]
        policy = original.cloneNode(deep=True)
        policies.renameNode(policy, "http://www.jcp.org/jcr/1.0", "jcr:root")
        for attribute in policies.documentElement.attributes.values():
            if attribute.name.startswith("xmlns:"):
                policy.setAttribute(attribute.name, attribute.value)
        policy.setAttribute("jcr:title", "WKND Adventure Demo Content")
        allowed = ["group:WKND.Content", "group:Weekend Content Demo",
                   *(f"/libs/{row[0]}" for row in CORE_COMPONENTS)]
        policy.setAttribute("components", "[" + ",".join(allowed) + "]")
        demo_policy = policy.toxml(encoding="UTF-8")
    template_files["policies/.content.xml"] = template_files["policies/.content.xml"].replace(
        f'cq:policy="{ORIGINAL_CONTAINER_POLICY}"'.encode(),
        f'cq:policy="{DEMO_CONTAINER_POLICY}"'.encode(),
    )
    page = page.replace(f'cq:template="{TEMPLATE_SOURCE}"', f'cq:template="{TEMPLATE_TARGET}"', 1)

    page, title_count = re.subn(
        'jcr:title="Bali Surf Camp"',
        'jcr:title="Bali Surf Camp — Demo"',
        page,
        count=1,
    )
    if title_count != 1:
        raise ValueError("Expected the Bali Surf Camp page title in WKND 4.0.4")
    page = page.replace(
        'jcr:description="Surfing in Bali',
        'jcr:description="Demo adventure. Surfing in Bali',
        1,
    )
    # Give the copy its own page identity outside the original MSM live copy.
    page = re.sub(
        r'^ *\s*(?:jcr:mixinTypes="\[cq:LiveRelationship\]"|cq:lastRolledout(?:By)?="[^"]*")\n',
        "",
        page,
        flags=re.MULTILINE,
    )
    with minidom.parseString(page) as document:
        tabs = document.getElementsByTagName("tabs")[0]
        bring_tab = next(
            child
            for child in tabs.childNodes
            if child.nodeType == child.ELEMENT_NODE
            and child.getAttribute("cq:panelTitle") == "What to Bring"
        )
        demo_tab = bring_tab.cloneNode(deep=True)
        document.renameNode(demo_tab, None, "demo")
        demo_tab.setAttribute("cq:panelTitle", "Demo")
        tabs.insertBefore(demo_tab, bring_tab.nextSibling)
        add_demo_components(document)
        page = document.toxml(encoding="UTF-8")
    section_page = build_section(landing_source)

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as package:
        package.writestr("META-INF/vault/filter.xml", FILTER)
        package.writestr("META-INF/vault/properties.xml", PROPERTIES)
        package.writestr(f"jcr_root{TARGET}/.content.xml", page)
        package.writestr(f"jcr_root{SECTION_TARGET}/.content.xml", section_page)
        write_jpeg_asset(package, SECTION_IMAGE, section_image, SECTION_IMAGE_DEFINITION)
        package.writestr(f"jcr_root{CATALOG_ASSETS}/.content.xml",
                         '<jcr:root xmlns:jcr="http://www.jcp.org/jcr/1.0" '
                         'xmlns:sling="http://sling.apache.org/jcr/sling/1.0" '
                         'jcr:primaryType="sling:Folder"/>')
        for item in CATALOG_PAGES:
            slug, title, _, _, _, photo_id = item
            package.writestr(f"jcr_root{SECTION_TARGET}/{slug}/.content.xml",
                             build_catalog_page(page, item))
            asset_definition = SECTION_IMAGE_DEFINITION.replace(
                'dc:title="Illustration of a component library"',
                f'dc:title="{escape(title)}" dc:source="https://www.pexels.com/photo/{photo_id}/"',
            )
            write_jpeg_asset(package, f"{CATALOG_ASSETS}/{slug}.jpg",
                             section_image.parent / "catalog-images" / f"{slug}.jpg",
                             asset_definition)
        clientlib = f"jcr_root{DEMO_CLIENTLIB}"
        package.writestr(f"{clientlib}/.content.xml", DEMO_CLIENTLIB_DEFINITION)
        package.writestr(f"{clientlib}/css.txt", "demo-components.css\n")
        package.writestr(f"{clientlib}/demo-components.css", DEMO_COMPONENTS_CSS)
        package.writestr(
            f"jcr_root{POLICY_ROOT}/{DEMO_CONTAINER_POLICY}/.content.xml", demo_policy,
        )
        package.writestr(f"{clientlib}/js.txt", "weather.js\n")
        package.write(weather_source / "clientlib/weather.js", f"{clientlib}/weather.js")
        for name in (".content.xml", "weather.html"):
            package.write(weather_source / "component" / name,
                          f"jcr_root{WEATHER_COMPONENT}/{name}")
        for name, data in template_files.items():
            package.writestr(f"jcr_root{TEMPLATE_TARGET}/{name}", data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wknd_release", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--weather-source", type=Path, default=Path("weather"))
    parser.add_argument("--section-image", type=Path, default=Path("content-package/demo-components.jpg"))
    args = parser.parse_args()
    build_package(args.wknd_release, args.output, args.weather_source, args.section_image)
