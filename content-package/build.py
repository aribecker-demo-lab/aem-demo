"""Build the FileVault content package from the pinned WKND release."""
import argparse
import io
import re
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

FILTER = f"""<?xml version="1.0" encoding="UTF-8"?>
<workspaceFilter version="1.0">
    <filter root="{TARGET}" mode="replace"/>
    <filter root="{TEMPLATE_TARGET}" mode="replace"/>
</workspaceFilter>
"""

PROPERTIES = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
    <entry key="group">wknd-demo</entry>
    <entry key="name">wknd-demo-adventure</entry>
    <entry key="version">1.0.0</entry>
    <entry key="packageType">content</entry>
    <entry key="dependencies">com.adobe.aem.guides:aem-guides-wknd.ui.content.sample:4.0.4</entry>
</properties>
"""


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
        component("demo_text", "text", text="<p>Text component example for Bali Surf Camp.</p>",
                  textIsRich="{Boolean}true"),
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
    for example in examples:
        body.insertBefore(example, first)


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
        for name, data in template_files.items():
            package.writestr(f"jcr_root{TEMPLATE_TARGET}/{name}", data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wknd_release", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_package(args.wknd_release, args.output)
