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
TEMPLATE_SOURCE = "/conf/wknd/settings/wcm/templates/adventure-page-template"
TEMPLATE_TARGET = f"{TEMPLATE_SOURCE}-demo"
DEMO_CLIENTLIB = "/apps/wknd/clientlibs/clientlib-demo-components"

FILTER = f"""<?xml version="1.0" encoding="UTF-8"?>
<workspaceFilter version="1.0">
    <filter root="{TARGET}" mode="replace"/>
    <filter root="{TEMPLATE_TARGET}" mode="replace"/>
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

DEMO_COMPONENTS_CSS = """#demo-components-frame {
    box-sizing: border-box;
    border: 6px solid #f00;
    padding: clamp(1rem, 3vw, 2rem);
    margin-block: 2rem;
}

#demo-components-frame #demo-components .cmp-title__text,
#demo-components-frame [id^="demo-label-"] h3 {
    color: #005d73;
    font-size: clamp(1.25rem, 2vw, 1.6rem);
    font-weight: 700;
    margin: 0 0 .35rem;
}

#demo-components-frame [id^="demo-meta-"] p {
    color: #343a40;
    margin: 0 0 1rem;
    overflow-wrap: anywhere;
}

#demo-components-frame .cmp-separator__horizontal-rule {
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
        node.setAttribute("sling:resourceType", f"wknd/components/{component_type}")
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
        frame.appendChild(example)
        if not label:
            frame.appendChild(metadata)
        frame.appendChild(component(f"{name}_divider", "separator"))
    body.insertBefore(frame, first)


def build_package(wknd_release: Path, output: Path) -> None:
    with ZipFile(wknd_release) as release:
        sample_bytes = release.read(SAMPLE_PACKAGE)
    with ZipFile(io.BytesIO(sample_bytes)) as sample:
        page = sample.read(f"jcr_root{SOURCE}/.content.xml").decode("utf-8")
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

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as package:
        package.writestr("META-INF/vault/filter.xml", FILTER)
        package.writestr("META-INF/vault/properties.xml", PROPERTIES)
        package.writestr(f"jcr_root{TARGET}/.content.xml", page)
        clientlib = f"jcr_root{DEMO_CLIENTLIB}"
        package.writestr(f"{clientlib}/.content.xml", DEMO_CLIENTLIB_DEFINITION)
        package.writestr(f"{clientlib}/css.txt", "demo-components.css\n")
        package.writestr(f"{clientlib}/demo-components.css", DEMO_COMPONENTS_CSS)
        for name, data in template_files.items():
            package.writestr(f"jcr_root{TEMPLATE_TARGET}/{name}", data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wknd_release", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_package(args.wknd_release, args.output)
