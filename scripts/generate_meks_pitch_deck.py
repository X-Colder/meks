#!/usr/bin/env python3
"""Generate a MEKS customer pitch deck without third-party dependencies."""

from __future__ import annotations

import html
import zipfile
from pathlib import Path


OUT = Path("docs/MEKS_医生科研AI知识库系统_路演材料.pptx")
SLIDE_W = 12192000
SLIDE_H = 6858000
EMU = 914400


def emu(inches: float) -> int:
    return int(inches * EMU)


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def rgb(color: str) -> str:
    return color.strip("#").upper()


class Deck:
    def __init__(self) -> None:
        self.slides: list[str] = []

    def add_slide(self, elements: list[str], bg: str = "F7F9FC") -> None:
        self.slides.append(slide_xml(elements, bg))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", content_types(len(self.slides)))
            z.writestr("_rels/.rels", root_rels())
            z.writestr("docProps/core.xml", core_props())
            z.writestr("docProps/app.xml", app_props(len(self.slides)))
            z.writestr("ppt/presentation.xml", presentation_xml(len(self.slides)))
            z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels(len(self.slides)))
            z.writestr("ppt/theme/theme1.xml", theme_xml())
            z.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml())
            z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", slide_master_rels())
            z.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml())
            z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels())
            for i, s in enumerate(self.slides, 1):
                z.writestr(f"ppt/slides/slide{i}.xml", s)
                z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", slide_rels())


def tx_body(text: str, size: int = 24, color: str = "1F2937", bold: bool = False,
            align: str = "l", bullet: bool = False, line_spacing: int = 110) -> str:
    paras = text.split("\n")
    out = ['<p:txBody><a:bodyPr wrap="square" lIns="91440" tIns="45720" rIns="91440" bIns="45720"/><a:lstStyle/>']
    for para in paras:
        para = para.strip()
        bu = '<a:buChar char="•"/>' if bullet and para else ""
        out.append(
            f'<a:p><a:pPr algn="{align}">{bu}<a:lnSpc><a:spcPct val="{line_spacing}000"/></a:lnSpc></a:pPr>'
            f'<a:r><a:rPr lang="zh-CN" sz="{size * 100}" {"b=\"1\"" if bold else ""}>'
            f'<a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill>'
            f'<a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:rPr>'
            f'<a:t>{esc(para)}</a:t></a:r></a:p>'
        )
    out.append("</p:txBody>")
    return "".join(out)


def shape(id_: int, x: float, y: float, w: float, h: float, text: str = "",
          fill: str | None = "FFFFFF", line: str | None = None, prst: str = "roundRect",
          size: int = 20, color: str = "1F2937", bold: bool = False,
          align: str = "l", bullet: bool = False, alpha: int | None = None) -> str:
    fill_xml = "<a:noFill/>" if fill is None else f'<a:solidFill><a:srgbClr val="{rgb(fill)}">' + (f'<a:alpha val="{alpha}"/>' if alpha else "") + '</a:srgbClr></a:solidFill>'
    line_xml = '<a:ln><a:noFill/></a:ln>' if line is None else f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{rgb(line)}"/></a:solidFill></a:ln>'
    body = tx_body(text, size=size, color=color, bold=bold, align=align, bullet=bullet) if text else '<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>'
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{id_}" name="Shape {id_}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
      <p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
        <a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>{fill_xml}{line_xml}</p:spPr>
      {body}
    </p:sp>"""


def title(text: str, subtitle: str | None = None) -> list[str]:
    elems = [
        shape(900, 0.45, 0.28, 0.18, 0.45, "", fill="1677FF", prst="rect"),
        shape(901, 0.72, 0.22, 8.8, 0.45, text, fill=None, size=25, bold=True, color="111827"),
    ]
    if subtitle:
        elems.append(shape(902, 0.72, 0.68, 10.5, 0.35, subtitle, fill=None, size=11, color="6B7280"))
    return elems


def stat_card(id_: int, x: float, y: float, label: str, value: str, note: str, color: str) -> str:
    return (
        shape(id_, x, y, 2.25, 1.15, "", fill="FFFFFF", line="E5E7EB")
        + shape(id_ + 1, x + 0.18, y + 0.14, 0.56, 0.56, value, fill=color, prst="ellipse", size=12, color="FFFFFF", bold=True, align="ctr")
        + shape(id_ + 2, x + 0.85, y + 0.12, 1.25, 0.28, label, fill=None, size=13, bold=True)
        + shape(id_ + 3, x + 0.85, y + 0.48, 1.25, 0.38, note, fill=None, size=9, color="6B7280")
    )


def pipeline(id_: int, y: float, labels: list[str]) -> list[str]:
    elems = []
    x = 0.8
    for i, label in enumerate(labels):
        elems.append(shape(id_ + i * 3, x, y, 1.75, 0.72, label, fill="EAF2FF", line="BBD6FF", size=12, bold=True, align="ctr"))
        if i < len(labels) - 1:
            elems.append(shape(id_ + i * 3 + 1, x + 1.78, y + 0.2, 0.45, 0.32, "", fill="1677FF", prst="rightArrow"))
        x += 2.18
    return elems


def slide_xml(elements: list[str], bg: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{rgb(bg)}"/></a:solidFill></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {''.join(elements)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''


def content_types(n: int) -> str:
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    overrides += [f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(1, n + 1)]
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {''.join(overrides)}
</Types>'''


def root_rels() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def presentation_xml(n: int) -> str:
    sids = "".join([f'<p:sldId id="{255+i}" r:id="rId{i+1}"/>' for i in range(1, n + 1)])
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
 <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
 <p:sldIdLst>{sids}</p:sldIdLst>
 <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="screen16x9"/>
 <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''


def presentation_rels(n: int) -> str:
    rels = ['<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    rels += [f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, n + 1)]
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{''.join(rels)}</Relationships>'''


def slide_master_xml() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
 <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
 <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
 <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
 <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>'''


def slide_master_rels() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>'''


def slide_layout_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank">
 <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
 <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>'''


def slide_layout_rels() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''


def slide_rels() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'''


def theme_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="MEKS">
 <a:themeElements>
  <a:clrScheme name="MEKS"><a:dk1><a:srgbClr val="111827"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F7F9FC"/></a:lt2><a:accent1><a:srgbClr val="1677FF"/></a:accent1><a:accent2><a:srgbClr val="10B981"/></a:accent2><a:accent3><a:srgbClr val="F59E0B"/></a:accent3><a:accent4><a:srgbClr val="EF4444"/></a:accent4><a:accent5><a:srgbClr val="6366F1"/></a:accent5><a:accent6><a:srgbClr val="14B8A6"/></a:accent6><a:hlink><a:srgbClr val="1677FF"/></a:hlink><a:folHlink><a:srgbClr val="6366F1"/></a:folHlink></a:clrScheme>
  <a:fontScheme name="MEKS"><a:majorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:majorFont><a:minorFont><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:minorFont></a:fontScheme>
  <a:fmtScheme name="MEKS"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/><a:bgFillStyleLst/></a:fmtScheme>
 </a:themeElements>
</a:theme>'''


def core_props() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>MEKS 医生科研 AI 知识库系统路演材料</dc:title><dc:creator>MEKS</dc:creator><cp:lastModifiedBy>MEKS</cp:lastModifiedBy></cp:coreProperties>'''


def app_props(n: int) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>MEKS</Application><PresentationFormat>宽屏</PresentationFormat><Slides>{n}</Slides></Properties>'''


def build_deck() -> Deck:
    d = Deck()

    d.add_slide([
        shape(2, 0.65, 0.55, 3.3, 0.52, "MEKS", fill="1677FF", prst="roundRect", size=24, color="FFFFFF", bold=True, align="ctr"),
        shape(3, 0.65, 1.45, 8.9, 1.35, "医生科研与医学知识工作台", fill=None, size=38, color="111827", bold=True),
        shape(4, 0.72, 2.9, 8.8, 0.6, "从前沿发现、文献精读、研究设计到论文写作的一体化 AI 知识库系统", fill=None, size=18, color="374151"),
        shape(5, 0.8, 4.25, 2.2, 0.78, "前沿追踪", fill="EAF2FF", line="BBD6FF", size=16, bold=True, align="ctr"),
        shape(6, 3.25, 4.25, 2.2, 0.78, "科研设计", fill="ECFDF5", line="A7F3D0", size=16, bold=True, align="ctr"),
        shape(7, 5.7, 4.25, 2.2, 0.78, "论文写作", fill="FFF7ED", line="FED7AA", size=16, bold=True, align="ctr"),
        shape(8, 8.15, 4.25, 2.2, 0.78, "安全私有化", fill="F5F3FF", line="DDD6FE", size=16, bold=True, align="ctr"),
        shape(9, 9.65, 0.55, 2.5, 4.9, "AI\n医学文献\n科研数据\n论文草稿", fill="FFFFFF", line="E5E7EB", size=22, bold=True, align="ctr"),
    ], bg="F7FAFF")

    d.add_slide(title("医生科研的真实痛点", "不是缺少信息，而是缺少把信息转化为论文和课题的工作流") + [
        stat_card(10, 0.8, 1.35, "文献太多", "01", "每天都有新论文，医生很难持续追踪", "1677FF"),
        stat_card(20, 3.35, 1.35, "时间太少", "02", "临床工作挤压科研阅读和写作时间", "10B981"),
        stat_card(30, 5.9, 1.35, "数据难用", "03", "病例与随访数据分散，难形成队列", "F59E0B"),
        stat_card(40, 8.45, 1.35, "产出压力", "04", "论文、课题、伦理、职称材料要求持续增长", "EF4444"),
        *pipeline(60, 3.55, ["临床问题", "文献证据", "研究假设", "数据设计", "论文产出"]),
        shape(90, 1.05, 5.45, 10.8, 0.55, "MEKS 解决的是“科研过程管理 + AI 证据增强”，不是替代医生做临床诊断。", fill="111827", prst="roundRect", size=17, color="FFFFFF", bold=True, align="ctr"),
    ])

    d.add_slide(title("产品定位", "面向三甲医院科室、青年医生、研究生和科研管理团队") + [
        shape(10, 0.85, 1.4, 3.2, 4.5, "医生个人\n\n• 每日文献雷达\n• 论文精读卡片\n• 草稿写作助手\n• 课题/伦理材料", fill="FFFFFF", line="D1D5DB", size=17, bold=True),
        shape(20, 4.35, 1.4, 3.2, 4.5, "科室团队\n\n• 共享知识库\n• 关注方向沉淀\n• 研究选题共创\n• 文献与病例素材", fill="FFFFFF", line="D1D5DB", size=17, bold=True),
        shape(30, 7.85, 1.4, 3.2, 4.5, "医院管理\n\n• 科研能力提升\n• 数据与权限审计\n• 本地化部署\n• 可持续试点推广", fill="FFFFFF", line="D1D5DB", size=17, bold=True),
    ])

    d.add_slide(title("核心卖点一：前沿发现", "关注点驱动，自动发现和同步新论文") + [
        shape(10, 0.8, 1.25, 2.55, 3.9, "关注点\n\n医生自定义疾病、技术、药物、标志物、研究人群等方向", fill="EAF2FF", line="BBD6FF", size=15),
        shape(20, 3.55, 1.25, 2.55, 3.9, "自动同步\n\n按天/周定时抓取论文，增量下载，跳过重复 DOI/PMCID", fill="ECFDF5", line="A7F3D0", size=15),
        shape(30, 6.3, 1.25, 2.55, 3.9, "前沿指数\n\n综合发布时间、证据类型、方法标签、索引状态评分", fill="FFF7ED", line="FED7AA", size=15),
        shape(40, 9.05, 1.25, 2.55, 3.9, "推荐理由\n\n告诉医生为什么值得读、是否可引用、是否适合做选题", fill="F5F3FF", line="DDD6FE", size=15),
        shape(50, 1.2, 5.55, 9.8, 0.45, "示例：心血管代谢与炎症 → 每天 8 点同步 50 篇 → 推荐“重点精读 / 建议浏览 / 背景材料”", fill="111827", color="FFFFFF", size=14, bold=True, align="ctr"),
    ])

    d.add_slide(title("核心卖点二：医学文献知识库", "让 PDF/XML/指南/综述变成可检索、可问答、可引用的知识资产") + [
        *pipeline(10, 1.35, ["上传/同步", "解析正文", "语义切分", "向量索引", "问答引用"]),
        shape(40, 0.85, 3.0, 2.6, 2.4, "语义检索\n\n不是关键词匹配，而是按研究问题找到相关段落", fill="FFFFFF", line="E5E7EB", size=15),
        shape(50, 3.75, 3.0, 2.6, 2.4, "证据溯源\n\n回答必须关联论文标题、作者、期刊和片段", fill="FFFFFF", line="E5E7EB", size=15),
        shape(60, 6.65, 3.0, 2.4, 2.4, "自动索引\n\n失败重试、手动重建索引，保证知识库可用", fill="FFFFFF", line="E5E7EB", size=15),
        shape(70, 9.25, 3.0, 2.4, 2.4, "科室沉淀\n\n把个人阅读转成科室长期可复用资产", fill="FFFFFF", line="E5E7EB", size=15),
    ])

    d.add_slide(title("核心卖点三：论文精读与可信度评估", "帮助医生快速判断一篇论文是否值得引用、值得精读") + [
        shape(10, 0.9, 1.3, 3.5, 4.5, "精读卡片\n\n• 研究问题\n• 研究设计\n• 样本量\n• 主要结局\n• 统计方法\n• 临床意义", fill="FFFFFF", line="E5E7EB", size=15),
        shape(20, 4.8, 1.3, 3.5, 4.5, "可信度评估\n\n• 数据统计\n• 逻辑一致性\n• 复现性\n• 图表一致性\n• 引用风险\n• 综合建议", fill="FFFFFF", line="E5E7EB", size=15),
        shape(30, 8.7, 1.3, 2.7, 4.5, "输出价值\n\n低成本完成文献预筛，减少误读和无效引用", fill="EAF2FF", line="BBD6FF", size=16, bold=True),
    ])

    d.add_slide(title("核心卖点四：研究设计助手", "把临床问题转化为可执行的科研方案") + [
        shape(10, 0.8, 1.1, 2.2, 1.0, "医生输入\n临床问题/病例资源", fill="EAF2FF", line="BBD6FF", size=14, bold=True, align="ctr"),
        shape(11, 3.2, 1.1, 2.2, 1.0, "AI 生成\nPICO/变量/终点", fill="ECFDF5", line="A7F3D0", size=14, bold=True, align="ctr"),
        shape(12, 5.6, 1.1, 2.2, 1.0, "系统匹配\n文献证据/类似研究", fill="FFF7ED", line="FED7AA", size=14, bold=True, align="ctr"),
        shape(13, 8.0, 1.1, 2.2, 1.0, "形成材料\n方案/CRF/SAP", fill="F5F3FF", line="DDD6FE", size=14, bold=True, align="ctr"),
        shape(20, 1.0, 3.0, 4.9, 2.6, "可输出内容\n\n• 研究题目建议\n• 纳入/排除标准\n• 变量表和数据字典\n• 统计分析计划\n• 伦理材料草稿", fill="FFFFFF", line="E5E7EB", size=15),
        shape(30, 6.4, 3.0, 4.9, 2.6, "医生价值\n\n• 降低科研入门门槛\n• 提高选题质量\n• 让临床资源变成研究资产\n• 方便科室内部协作", fill="FFFFFF", line="E5E7EB", size=15),
    ])

    d.add_slide(title("核心卖点五：论文写作协作", "AI 给灵感，医生掌控正式草稿") + [
        shape(10, 0.85, 1.25, 5.2, 4.7, "左侧：AI 研究对话\n\n• 持续追问和分析\n• 解释最新研究成果\n• 生成可写入片段\n• 对话记录保留\n• 选中片段插入草稿", fill="FFFFFF", line="D1D5DB", size=16),
        shape(20, 6.55, 1.25, 5.2, 4.7, "右侧：正式草稿\n\n• 医生直接编辑\n• 实时 Markdown 预览\n• Word/PDF 导出\n• 斜置多水印\n• 不再把 AI 回复自动污染正文", fill="FFFFFF", line="D1D5DB", size=16),
    ])

    d.add_slide(title("客户演示路径", "10 分钟让医生看到完整闭环") + [
        *pipeline(10, 1.1, ["建关注点", "自动同步", "精读论文", "设计课题", "生成草稿"]),
        shape(40, 0.9, 2.8, 10.8, 2.7, "演示脚本\n\n1. 创建“心衰 + 炎症标志物”关注点并自动下载论文\n2. 查看前沿推荐列表和趋势关键词\n3. 打开一篇论文，查看精读/鉴真结果\n4. 基于论文问 AI：还能形成哪些研究假设？\n5. 选中 AI 片段插入右侧论文草稿，预览并导出 Word/PDF", fill="FFFFFF", line="E5E7EB", size=16),
    ])

    d.add_slide(title("差异化优势", "不是一个聊天框，而是面向医生科研产出的系统") + [
        shape(10, 0.8, 1.15, 2.6, 4.7, "通用大模型\n\n• 临时问答\n• 无本地知识沉淀\n• 缺少权限审计\n• 难以连接科研工作流", fill="FEE2E2", line="FCA5A5", size=15),
        shape(20, 3.75, 1.15, 2.6, 4.7, "传统文献管理\n\n• 管 PDF 和引用\n• 不理解研究问题\n• 不自动发现前沿\n• 不辅助写作和课题", fill="FEF3C7", line="FCD34D", size=15),
        shape(30, 6.7, 1.15, 2.6, 4.7, "MEKS\n\n• 前沿发现\n• 私有知识库\n• 证据溯源\n• 科研设计\n• 论文协作\n• 本地部署", fill="DCFCE7", line="86EFAC", size=15),
        shape(40, 9.65, 1.15, 2.6, 4.7, "医院价值\n\n• 科研提效\n• 科室资产沉淀\n• 青年医生培养\n• 院内合规可控", fill="DBEAFE", line="93C5FD", size=15),
    ])

    d.add_slide(title("部署与合规", "先轻量试点，再接入院内数据") + [
        shape(10, 0.9, 1.2, 3.2, 4.6, "第一阶段\n公开文献 + 上传资料\n\n• 无需接 HIS\n• 快速验证价值\n• 科室级试点", fill="FFFFFF", line="E5E7EB", size=16),
        shape(20, 4.5, 1.2, 3.2, 4.6, "第二阶段\n院内私有化部署\n\n• 访问控制\n• 审计日志\n• 数据隔离\n• 模型网关", fill="FFFFFF", line="E5E7EB", size=16),
        shape(30, 8.1, 1.2, 3.2, 4.6, "第三阶段\n科研数据治理\n\n• 病例抽取\n• 队列构建\n• CRF/数据字典\n• 研究型病房", fill="FFFFFF", line="E5E7EB", size=16),
    ])

    d.add_slide(title("试点建议", "建议从 1-2 个科研活跃科室切入") + [
        shape(10, 0.9, 1.1, 2.55, 4.5, "试点对象\n\n• 心血管\n• 肿瘤\n• 神经内科\n• 呼吸\n• 内分泌\n• 药学/检验", fill="FFFFFF", line="E5E7EB", size=16),
        shape(20, 3.75, 1.1, 2.55, 4.5, "试点周期\n\n4-8 周\n\n• 配置关注点\n• 建知识库\n• 训练使用流程\n• 收集产出案例", fill="FFFFFF", line="E5E7EB", size=16),
        shape(30, 6.6, 1.1, 2.55, 4.5, "验收指标\n\n• 新论文发现量\n• 精读节省时间\n• 草稿产出数量\n• 课题方向数量", fill="FFFFFF", line="E5E7EB", size=16),
        shape(40, 9.45, 1.1, 2.55, 4.5, "扩展路径\n\n科室试点 → 多科室复制 → 科研处平台 → 院内数据接入", fill="FFFFFF", line="E5E7EB", size=16),
    ])

    d.add_slide(title("产品路线图", "围绕医生科研产出持续增强") + [
        shape(10, 1.0, 1.25, 2.4, 3.8, "V1 已具备\n\n• 前沿发现\n• 文献知识库\n• 论文鉴真\n• AI 写作草稿\n• Word/PDF 导出", fill="EAF2FF", line="BBD6FF", size=15),
        shape(20, 3.75, 1.25, 2.4, 3.8, "V2 重点\n\n• 论文精读卡片\n• 研究设计助手\n• 引用管理\n• 伦理/标书模板", fill="ECFDF5", line="A7F3D0", size=15),
        shape(30, 6.5, 1.25, 2.4, 3.8, "V3 扩展\n\n• 病例结构化\n• 队列构建\n• 数据字典\n• 统计分析计划", fill="FFF7ED", line="FED7AA", size=15),
        shape(40, 9.25, 1.25, 2.4, 3.8, "V4 平台化\n\n• 院级知识库\n• 科研项目管理\n• 多模型网关\n• 合规审计", fill="F5F3FF", line="DDD6FE", size=15),
    ])

    d.add_slide([
        shape(10, 0.8, 0.75, 4.0, 0.6, "MEKS", fill="1677FF", prst="roundRect", size=26, color="FFFFFF", bold=True, align="ctr"),
        shape(20, 0.9, 1.65, 10.4, 1.0, "把医生每天遇到的临床问题，转化为可沉淀、可协作、可发表的科研产出", fill=None, size=30, color="111827", bold=True, align="ctr"),
        shape(30, 2.1, 3.35, 8.8, 0.75, "建议下一步：选择 1 个科研活跃科室，启动 4 周试点", fill="111827", color="FFFFFF", size=20, bold=True, align="ctr"),
        shape(40, 3.2, 4.55, 6.6, 0.65, "前沿发现 + 文献精读 + 论文草稿：先做出医生可感知的产出", fill="FFFFFF", line="E5E7EB", size=16, align="ctr"),
    ], bg="F7FAFF")

    return d


def main() -> None:
    deck = build_deck()
    deck.save(OUT)
    print(f"Wrote {OUT.resolve()}")


if __name__ == "__main__":
    main()
