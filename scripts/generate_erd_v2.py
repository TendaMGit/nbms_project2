import ast
import html
import uuid
from datetime import datetime, timezone
from pathlib import Path

# --- Step 1: Parse existing drawio to confirm Mermaid erDiagram ---
existing_drawio = Path("docs/ops/db_schema.drawio")
if existing_drawio.exists():
    xml_text = existing_drawio.read_text(encoding="utf-8")
    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)
        mermaid_cells = []
        for cell in root.iter("mxCell"):
            style = cell.get("style", "")
            if "mxgraph.mermaid" in style:
                mermaid_cells.append(cell.get("value", ""))
        if mermaid_cells:
            decoded = html.unescape(mermaid_cells[0])
            if "erDiagram" not in decoded:
                raise RuntimeError("Existing drawio Mermaid is not an erDiagram")
    except Exception as exc:
        raise SystemExit(f"Failed to parse existing drawio: {exc}")

# --- Step 2: Parse models.py ---
source_path = Path("src/nbms_app/models.py")
source = source_path.read_text(encoding="utf-8")
tree = ast.parse(source)


def get_attr_chain(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = get_attr_chain(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def call_func_name(call):
    if isinstance(call.func, ast.Attribute):
        base = get_attr_chain(call.func.value)
        return f"{base}.{call.func.attr}" if base else call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return None


def kw_value(call, name):
    for kw in call.keywords:
        if kw.arg == name:
            if isinstance(kw.value, ast.Constant):
                return kw.value.value
            if isinstance(kw.value, ast.NameConstant):
                return kw.value.value
    return None


# Collect class bases
class_bases = {}
class_defs = {}
for node in tree.body:
    if isinstance(node, ast.ClassDef):
        bases = [get_attr_chain(b) for b in node.bases]
        class_bases[node.name] = bases
        class_defs[node.name] = node

# Identify model classes
model_classes = set()
for name, bases in class_bases.items():
    if any(b in ("models.Model", "AbstractUser") for b in bases):
        model_classes.add(name)

# Include subclasses of model classes
changed = True
while changed:
    changed = False
    for name, bases in class_bases.items():
        if name in model_classes:
            continue
        if any(b in model_classes for b in bases):
            model_classes.add(name)
            changed = True


# Identify abstract models
def is_abstract(classdef):
    for node in classdef.body:
        if isinstance(node, ast.ClassDef) and node.name == "Meta":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "abstract":
                            if isinstance(stmt.value, ast.Constant) and stmt.value.value is True:
                                return True
    return False


abstract_models = {name for name in model_classes if is_abstract(class_defs[name])}


def inherits_from(model_name, base_name):
    if model_name == base_name:
        return True
    for base in class_bases.get(model_name, []):
        if base == base_name:
            return True
        if base in class_bases and inherits_from(base, base_name):
            return True
    return False


# Format field types
def format_field_type(field_type, call):
    if field_type in ("CharField", "EmailField", "URLField"):
        max_length = kw_value(call, "max_length")
        if max_length is None and call.args:
            if isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, int):
                max_length = call.args[0].value
        return f"string({max_length})" if max_length else "string"
    if field_type == "TextField":
        return "text"
    if field_type == "UUIDField":
        return "uuid"
    if field_type == "DateField":
        return "date"
    if field_type == "DateTimeField":
        return "datetime"
    if field_type == "BooleanField":
        return "boolean"
    if field_type in ("IntegerField", "PositiveIntegerField", "PositiveSmallIntegerField", "SmallIntegerField"):
        return "int"
    if field_type == "BigIntegerField":
        return "bigint"
    if field_type == "DecimalField":
        max_digits = kw_value(call, "max_digits")
        decimal_places = kw_value(call, "decimal_places")
        if max_digits is None and call.args:
            if isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, int):
                max_digits = call.args[0].value
        if decimal_places is None and len(call.args) > 1:
            if isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, int):
                decimal_places = call.args[1].value
        if max_digits is not None and decimal_places is not None:
            return f"decimal({max_digits},{decimal_places})"
        return "decimal"
    if field_type == "FloatField":
        return "float"
    if field_type == "JSONField":
        return "json"
    if field_type in ("FileField", "ImageField"):
        return "file"
    return field_type.lower()


models_info = {}
relationships = []  # (src, tgt, field_name, rel_type, nullable)

for model_name in sorted(model_classes):
    if model_name in abstract_models:
        continue
    classdef = class_defs[model_name]
    fields = []

    # implicit id (BigAutoField by default)
    fields.append({"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"})

    # timestamps
    if inherits_from(model_name, "TimeStampedModel"):
        fields.append({"name": "created_at", "type": "datetime", "tag": None, "kind": "field"})
        fields.append({"name": "updated_at", "type": "datetime", "tag": None, "kind": "field"})

    for stmt in classdef.body:
        if isinstance(stmt, ast.Assign):
            targets = stmt.targets
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            targets = [stmt.target]
            value = stmt.value
        else:
            continue
        if not isinstance(value, ast.Call):
            continue
        func_name = call_func_name(value)
        if not func_name or not func_name.startswith("models."):
            continue
        field_type = func_name.split(".", 1)[1]

        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            field_name = target.id

            if field_type in ("ForeignKey", "OneToOneField"):
                # target model name
                if value.args:
                    arg = value.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        target_model = model_name if arg.value == "self" else arg.value
                    elif isinstance(arg, ast.Name):
                        target_model = arg.id
                    elif isinstance(arg, ast.Attribute):
                        chain = get_attr_chain(arg)
                        target_model = "User" if chain == "settings.AUTH_USER_MODEL" else chain.split(".", 1)[-1]
                    else:
                        target_model = None
                else:
                    target_model = None
                nullable = kw_value(value, "null") is True
                fields.append(
                    {
                        "name": field_name,
                        "type": "fk",
                        "tag": "FK",
                        "kind": "fk",
                        "target": target_model,
                        "nullable": nullable,
                    }
                )
                relationships.append((model_name, target_model, field_name, field_type, nullable))
            elif field_type == "ManyToManyField":
                # ignore for fields; handled separately if needed
                continue
            else:
                dtype = format_field_type(field_type, value)
                fields.append({"name": field_name, "type": dtype, "tag": None, "kind": "field"})

    models_info[model_name] = fields
# Override/augment User and ContentType
models_info["User"] = [
    {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
    {"name": "username", "type": "string(150)", "tag": None, "kind": "field"},
    {"name": "email", "type": "string(254)", "tag": None, "kind": "field"},
    {"name": "first_name", "type": "string(150)", "tag": None, "kind": "field"},
    {"name": "last_name", "type": "string(150)", "tag": None, "kind": "field"},
    {"name": "is_active", "type": "boolean", "tag": None, "kind": "field"},
    {"name": "is_staff", "type": "boolean", "tag": None, "kind": "field"},
    {"name": "is_superuser", "type": "boolean", "tag": None, "kind": "field"},
    {"name": "last_login", "type": "datetime", "tag": None, "kind": "field"},
    {"name": "date_joined", "type": "datetime", "tag": None, "kind": "field"},
    {"name": "organisation", "type": "fk", "tag": "FK", "kind": "fk", "target": "Organisation", "nullable": True},
]

models_info["ContentType"] = [
    {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
    {"name": "app_label", "type": "string(100)", "tag": None, "kind": "field"},
    {"name": "model", "type": "string(100)", "tag": None, "kind": "field"},
]


# --- Field selection helpers ---
core_fields = {
    "Organisation": ["id", "name", "org_code", "org_type", "parent_org", "is_active"],
    "User": ["id", "username", "email", "first_name", "last_name", "is_active", "is_staff", "organisation"],
    "Framework": ["id", "uuid", "code", "title", "status", "organisation"],
    "FrameworkGoal": ["id", "uuid", "framework", "code", "title", "status", "is_active"],
    "FrameworkTarget": ["id", "uuid", "framework", "goal", "code", "title", "status"],
    "FrameworkIndicator": ["id", "uuid", "framework", "framework_target", "code", "title", "indicator_type", "status"],
    "NationalTarget": ["id", "uuid", "code", "title", "responsible_org", "status"],
    "Indicator": [
        "id",
        "uuid",
        "code",
        "title",
        "national_target",
        "indicator_type",
        "reporting_cadence",
        "status",
        "responsible_org",
        "organisation",
    ],
    "IndicatorDataSeries": ["id", "uuid", "framework_indicator", "indicator", "title", "unit", "value_type", "status"],
    "IndicatorDataPoint": ["id", "uuid", "series", "year", "value_numeric", "value_text"],
    "DatasetCatalog": ["id", "uuid", "dataset_code", "title", "custodian_org", "producer_org", "access_level", "is_active"],
    "Dataset": ["id", "uuid", "title", "organisation", "status", "sensitivity"],
    "DatasetRelease": ["id", "uuid", "dataset", "version", "release_date", "status"],
    "Evidence": ["id", "uuid", "title", "evidence_type", "organisation", "status", "sensitivity"],
    "ReportingCycle": ["id", "uuid", "code", "title", "start_date", "end_date", "due_date", "is_active"],
    "ReportingInstance": ["id", "uuid", "cycle", "version_label", "status", "frozen_at", "frozen_by"],
    "ExportPackage": ["id", "uuid", "title", "status", "reporting_instance", "organisation", "generated_at", "released_at"],
    "ConsentRecord": ["id", "uuid", "content_type", "object_uuid", "reporting_instance", "status", "granted_by", "granted_at"],
    "AuditEvent": ["id", "created_at", "actor", "action", "event_type", "content_type", "object_type", "object_uuid"],
    "ContentType": ["id", "app_label", "model"],
    "NationalTargetFrameworkTargetLink": ["id", "national_target", "framework_target", "relation_type", "confidence", "is_active"],
    "IndicatorFrameworkIndicatorLink": ["id", "indicator", "framework_indicator", "relation_type", "confidence", "is_active"],
    "IndicatorEvidenceLink": ["id", "indicator", "evidence", "note"],
    "IndicatorDatasetLink": ["id", "indicator", "dataset", "note"],
    "DatasetCatalogIndicatorLink": ["id", "dataset", "indicator", "relationship_type", "role", "is_active"],
}

anchor_fields = {
    "Organisation": ["id", "name", "org_code"],
    "User": ["id", "username", "email", "is_active", "organisation"],
    "Indicator": ["id", "code", "title"],
    "NationalTarget": ["id", "code", "title"],
    "FrameworkGoal": ["id", "code", "title"],
    "FrameworkTarget": ["id", "code", "title"],
    "FrameworkIndicator": ["id", "code", "title", "indicator_type"],
    "IndicatorDataSeries": ["id", "title", "value_type"],
    "IndicatorDataPoint": ["id", "year", "value_numeric", "value_text"],
    "DatasetRelease": ["id", "version", "release_date"],
    "Evidence": ["id", "title", "evidence_type"],
    "DatasetCatalog": ["id", "dataset_code", "title"],
    "ReportingInstance": ["id", "version_label", "status"],
    "BinaryIndicatorQuestion": ["id", "question_key", "question_type"],
    "BinaryIndicatorGroup": ["id", "key", "title"],
    "ReportingCycle": ["id", "code", "title"],
    "SourceDocument": ["id", "title", "source_url"],
    "License": ["id", "code", "title"],
    "Methodology": ["id", "methodology_code", "title"],
    "MethodologyVersion": ["id", "version", "status"],
    "Dataset": ["id", "title"],
    "MonitoringProgramme": ["id", "programme_code", "title"],
    "ContentType": ["id", "app_label", "model"],
}


def select_fields(model, mode):
    fields = models_info.get(model, [])
    by_name = {f["name"]: f for f in fields}
    if mode == "full":
        return fields
    if mode == "core":
        desired = core_fields.get(model)
    elif mode == "anchor":
        desired = anchor_fields.get(model)
    else:
        desired = None
    if not desired:
        # fallback: id + name/code/title if present
        desired = ["id"]
        for cand in ("name", "code", "title"):
            if cand in by_name:
                desired.append(cand)
                break
    result = []
    for name in desired:
        if name in by_name:
            result.append(by_name[name])
    return result


def field_line(f):
    line = f"    {f['type']} {f['name']}"
    if f.get("tag"):
        line += f" {f['tag']}"
    return line


def format_relationship(src, tgt, field_name, rel_type, nullable):
    if tgt is None:
        return None
    if rel_type == "ForeignKey":
        left = "||"
        right = "o{" if nullable else "|{"
        return f'  {tgt} {left}--{right} {src} : "{field_name}"'
    if rel_type == "OneToOneField":
        left = "||"
        right = "o|" if nullable else "||"
        return f'  {tgt} {left}--{right} {src} : "{field_name}"'
    return None


# --- Extra entities: implicit M2M join tables ---
def m2m_join_table(name, left_model, right_model, left_col, right_col):
    entity = {
        "name": name,
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": left_col, "type": "fk", "tag": "FK", "kind": "fk", "target": left_model, "nullable": False},
            {"name": right_col, "type": "fk", "tag": "FK", "kind": "fk", "target": right_model, "nullable": False},
        ],
    }
    rels = [
        (name, left_model, left_col, "ForeignKey", False),
        (name, right_model, right_col, "ForeignKey", False),
    ]
    return entity, rels


# --- Page definitions ---
pages = []

# 00 Legend
legend_lines = [
    "erDiagram",
    "  %% Legend and conventions",
    "  Legend_Notation {",
    "    string PK_primary_key",
    "    string FK_foreign_key",
    "    string UUID_universally_unique_id",
    "    string GFK_content_type_plus_object_uuid",
    "    string M2M_shown_via_through_table",
    "    string STATUS_status_or_lifecycle",
    "  }",
    "",
    "  Legend_TBI {",
    "    string AS_IS_existing_django_models",
    "    string TBI_prefix_for_future_tables",
    "    string _2bi_suffix_for_future_tables",
    "    string AUTO_M2M_tables_prefix_nbms_app",
    "  }",
    "",
    "  UserCore {",
    "    bigint id PK",
    "    string(150) username",
    "    string(254) email",
    "    string(150) first_name",
    "    string(150) last_name",
    "    boolean is_active",
    "    boolean is_staff",
    "    boolean is_superuser",
    "    datetime last_login",
    "    datetime date_joined",
    "    fk organisation FK",
    "  }",
]
pages.append(
    {
        "name": "00-LEGEND",
        "filename": "Page-00-LEGEND.mmd",
        "mermaid": "\n".join(legend_lines) + "\n",
    }
)
# Helper to render a page from entities
def render_page(name, filename, entity_modes, extra_entities=None, extra_rels=None, comments=None):
    lines = ["erDiagram"]
    if comments:
        for c in comments:
            lines.append(f"  %% {c}")
    lines.append("")

    included_fields = {}

    # Render entities in order
    for entity_name, mode in entity_modes:
        fields = select_fields(entity_name, mode)
        included_fields[entity_name] = {f["name"] for f in fields}
        lines.append(f"  {entity_name} {{")
        for f in fields:
            lines.append(field_line(f))
        lines.append("  }")
        lines.append("")

    # Extra entities
    extra_entities = extra_entities or []
    for ent in extra_entities:
        included_fields[ent["name"]] = {f["name"] for f in ent["fields"]}
        lines.append(f"  {ent['name']} {{")
        for f in ent["fields"]:
            lines.append(field_line(f))
        lines.append("  }")
        lines.append("")

    # Relationships
    rel_lines = []
    page_entity_names = set(included_fields.keys())
    for (src, tgt, field_name, rel_type, nullable) in relationships:
        if src in page_entity_names and tgt in page_entity_names:
            if field_name in included_fields.get(src, set()):
                line = format_relationship(src, tgt, field_name, rel_type, nullable)
                if line:
                    rel_lines.append(line)

    # Extra relationships
    extra_rels = extra_rels or []
    for (src, tgt, field_name, rel_type, nullable) in extra_rels:
        line = format_relationship(src, tgt, field_name, rel_type, nullable)
        if line:
            rel_lines.append(line)

    for line in rel_lines:
        lines.append(line)

    mermaid = "\n".join(lines).rstrip() + "\n"
    pages.append(
        {
            "name": name,
            "filename": filename,
            "mermaid": mermaid,
        }
    )


# 01 Core
core_entities = [
    ("Organisation", "core"),
    ("User", "core"),
    ("ContentType", "core"),
    ("Framework", "core"),
    ("FrameworkGoal", "core"),
    ("FrameworkTarget", "core"),
    ("FrameworkIndicator", "core"),
    ("NationalTarget", "core"),
    ("Indicator", "core"),
    ("IndicatorDataSeries", "core"),
    ("IndicatorDataPoint", "core"),
    ("DatasetCatalog", "core"),
    ("Dataset", "core"),
    ("DatasetRelease", "core"),
    ("Evidence", "core"),
    ("ReportingCycle", "core"),
    ("ReportingInstance", "core"),
    ("ExportPackage", "core"),
    ("ConsentRecord", "core"),
    ("AuditEvent", "core"),
    ("NationalTargetFrameworkTargetLink", "core"),
    ("IndicatorFrameworkIndicatorLink", "core"),
    ("IndicatorDatasetLink", "core"),
    ("IndicatorEvidenceLink", "core"),
    ("DatasetCatalogIndicatorLink", "core"),
]
render_page(
    "01-CORE-ERD",
    "Page-01-CORE.mmd",
    core_entities,
    comments=[
        "Core backbone entities only (AS-IS).",
        "User fields are inherited from AbstractUser plus organisation FK.",
    ],
)

# 02 Frameworks / Targets / Indicators
framework_entities = [
    ("Organisation", "anchor"),
    ("User", "anchor"),
    ("Framework", "full"),
    ("FrameworkGoal", "full"),
    ("FrameworkTarget", "full"),
    ("FrameworkIndicator", "full"),
    ("NationalTarget", "full"),
    ("Indicator", "full"),
    ("SourceDocument", "full"),
    ("License", "full"),
    ("NationalTargetFrameworkTargetLink", "full"),
    ("IndicatorFrameworkIndicatorLink", "full"),
    ("BinaryIndicatorGroup", "full"),
    ("BinaryIndicatorQuestion", "full"),
    ("IndicatorDataSeries", "full"),
    ("IndicatorDataPoint", "full"),
]
render_page(
    "02-FRAMEWORKS-TARGETS-INDICATORS",
    "Page-02-FRAMEWORKS.mmd",
    framework_entities,
    comments=[
        "Frameworks, targets, indicators, and binary indicator definitions (AS-IS).",
    ],
)

# 03 Datasets / Catalog / Releases / Evidence
extra_entities = []
extra_rels = []

# DataAgreement parties join table
ent, rels = m2m_join_table(
    "nbms_app_dataagreement_parties",
    "DataAgreement",
    "Organisation",
    "dataagreement_id",
    "organisation_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

# MonitoringProgramme partners join table
ent, rels = m2m_join_table(
    "nbms_app_monitoringprogramme_partners",
    "MonitoringProgramme",
    "Organisation",
    "monitoringprogramme_id",
    "organisation_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)


data_entities = [
    ("Organisation", "anchor"),
    ("User", "anchor"),
    ("SensitivityClass", "full"),
    ("DataAgreement", "full"),
    ("DatasetCatalog", "full"),
    ("Dataset", "full"),
    ("DatasetRelease", "full"),
    ("Evidence", "full"),
    ("DatasetCatalogIndicatorLink", "full"),
    ("IndicatorDatasetLink", "full"),
    ("IndicatorEvidenceLink", "full"),
    ("MonitoringProgramme", "full"),
    ("ProgrammeDatasetLink", "full"),
    ("ProgrammeIndicatorLink", "full"),
    ("Indicator", "anchor"),
]
render_page(
    "03-DATASETS-CATALOG-RELEASES-EVIDENCE",
    "Page-03-DATASETS.mmd",
    data_entities,
    extra_entities=extra_entities,
    extra_rels=extra_rels,
    comments=[
        "Datasets, catalog, releases, evidence, monitoring programmes, and link tables (AS-IS).",
        "Implicit M2M tables use Django default db_table naming (nbms_app_*).",
    ],
)

# 04 Methodologies / Validation / Readiness
method_entities = [
    ("Organisation", "anchor"),
    ("User", "anchor"),
    ("Methodology", "full"),
    ("MethodologyVersion", "full"),
    ("MethodologyDatasetLink", "full"),
    ("MethodologyIndicatorLink", "full"),
    ("IndicatorMethodologyVersionLink", "full"),
    ("ValidationRuleSet", "full"),
    ("ReportingSnapshot", "full"),
    ("ReportingInstance", "anchor"),
    ("Indicator", "anchor"),
    ("DatasetCatalog", "anchor"),
]
render_page(
    "04-METHODOLOGIES-VALIDATION-READINESS",
    "Page-04-METHODOLOGY.mmd",
    method_entities,
    comments=[
        "Methodologies, versions, validation rules, and readiness snapshots (AS-IS).",
    ],
)
# 05 Reporting / ORT Sections / Snapshots
extra_entities = []
extra_rels = []

# Section III M2M tables
ent, rels = m2m_join_table(
    "nbms_app_sectioniiinationaltargetprogress_indicator_data_series",
    "SectionIIINationalTargetProgress",
    "IndicatorDataSeries",
    "sectioniiinationaltargetprogress_id",
    "indicatordataseries_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

ent, rels = m2m_join_table(
    "nbms_app_sectioniiinationaltargetprogress_binary_indicator_responses",
    "SectionIIINationalTargetProgress",
    "BinaryIndicatorResponse",
    "sectioniiinationaltargetprogress_id",
    "binaryindicatorresponse_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

ent, rels = m2m_join_table(
    "nbms_app_sectioniiinationaltargetprogress_evidence_items",
    "SectionIIINationalTargetProgress",
    "Evidence",
    "sectioniiinationaltargetprogress_id",
    "evidence_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

ent, rels = m2m_join_table(
    "nbms_app_sectioniiinationaltargetprogress_dataset_releases",
    "SectionIIINationalTargetProgress",
    "DatasetRelease",
    "sectioniiinationaltargetprogress_id",
    "datasetrelease_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

# Section IV Target Progress M2M tables
ent, rels = m2m_join_table(
    "nbms_app_sectionivframeworktargetprogress_indicator_data_series",
    "SectionIVFrameworkTargetProgress",
    "IndicatorDataSeries",
    "sectionivframeworktargetprogress_id",
    "indicatordataseries_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

ent, rels = m2m_join_table(
    "nbms_app_sectionivframeworktargetprogress_binary_indicator_responses",
    "SectionIVFrameworkTargetProgress",
    "BinaryIndicatorResponse",
    "sectionivframeworktargetprogress_id",
    "binaryindicatorresponse_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

ent, rels = m2m_join_table(
    "nbms_app_sectionivframeworktargetprogress_evidence_items",
    "SectionIVFrameworkTargetProgress",
    "Evidence",
    "sectionivframeworktargetprogress_id",
    "evidence_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

ent, rels = m2m_join_table(
    "nbms_app_sectionivframeworktargetprogress_dataset_releases",
    "SectionIVFrameworkTargetProgress",
    "DatasetRelease",
    "sectionivframeworktargetprogress_id",
    "datasetrelease_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

# Section IV Goal Progress M2M tables
ent, rels = m2m_join_table(
    "nbms_app_sectionivframeworkgoalprogress_evidence_items",
    "SectionIVFrameworkGoalProgress",
    "Evidence",
    "sectionivframeworkgoalprogress_id",
    "evidence_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

# Section V Conclusions M2M tables
ent, rels = m2m_join_table(
    "nbms_app_sectionvconclusions_evidence_items",
    "SectionVConclusions",
    "Evidence",
    "sectionvconclusions_id",
    "evidence_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)

reporting_entities = [
    ("ReportingCycle", "full"),
    ("ReportingInstance", "full"),
    ("ReportingSnapshot", "full"),
    ("ReviewDecision", "full"),
    ("ReportSectionTemplate", "full"),
    ("ReportSectionResponse", "full"),
    ("SectionIReportContext", "full"),
    ("SectionIINBSAPStatus", "full"),
    ("SectionIIINationalTargetProgress", "full"),
    ("SectionIVFrameworkGoalProgress", "full"),
    ("SectionIVFrameworkTargetProgress", "full"),
    ("SectionVConclusions", "full"),
    ("BinaryIndicatorGroupResponse", "full"),
    ("BinaryIndicatorResponse", "full"),
    ("ExportPackage", "full"),
    ("User", "anchor"),
    ("NationalTarget", "anchor"),
    ("FrameworkTarget", "anchor"),
    ("FrameworkGoal", "anchor"),
    ("IndicatorDataSeries", "anchor"),
    ("BinaryIndicatorQuestion", "anchor"),
    ("BinaryIndicatorGroup", "anchor"),
    ("Evidence", "anchor"),
    ("DatasetRelease", "anchor"),
]
render_page(
    "05-REPORTING-ORT-SECTIONS-SNAPSHOTS",
    "Page-05-REPORTING.mmd",
    reporting_entities,
    extra_entities=extra_entities,
    extra_rels=extra_rels,
    comments=[
        "Reporting cycles, instances, sections, snapshots, and responses (AS-IS).",
        "Implicit M2M tables use Django default db_table naming (nbms_app_*).",
    ],
)

# 06 Governance / Consent / Approval / Audit
extra_entities = []
extra_rels = []

ent, rels = m2m_join_table(
    "nbms_app_dataagreement_parties",
    "DataAgreement",
    "Organisation",
    "dataagreement_id",
    "organisation_id",
)
extra_entities.append(ent)
extra_rels.extend(rels)


gov_entities = [
    ("Organisation", "full"),
    ("User", "anchor"),
    ("ContentType", "anchor"),
    ("ReportingInstance", "anchor"),
    ("ConsentRecord", "full"),
    ("InstanceExportApproval", "full"),
    ("AuditEvent", "full"),
    ("Notification", "full"),
    ("DataAgreement", "full"),
    ("SensitivityClass", "full"),
    ("License", "full"),
]
render_page(
    "06-GOVERNANCE-CONSENT-APPROVAL-AUDIT",
    "Page-06-GOVERNANCE.mmd",
    gov_entities,
    extra_entities=extra_entities,
    extra_rels=extra_rels,
    comments=[
        "Governance, consent, approval, audit, and reference policy tables (AS-IS).",
        "Implicit M2M tables use Django default db_table naming (nbms_app_*).",
    ],
)

# 07 Integration _2bi (TO-BE)
TBI_entities = []

TBI_entities.append(
    {
        "name": "TBI_SdgGoal_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "code", "type": "string(20)", "tag": None, "kind": "field"},
            {"name": "title", "type": "string(255)", "tag": None, "kind": "field"},
            {"name": "description", "type": "text", "tag": None, "kind": "field"},
            {"name": "is_active", "type": "boolean", "tag": None, "kind": "field"},
        ],
    }
)

TBI_entities.append(
    {
        "name": "TBI_SdgTarget_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "goal_id", "type": "fk", "tag": "FK", "kind": "fk", "target": "TBI_SdgGoal_2bi", "nullable": False},
            {"name": "code", "type": "string(20)", "tag": None, "kind": "field"},
            {"name": "title", "type": "string(255)", "tag": None, "kind": "field"},
            {"name": "description", "type": "text", "tag": None, "kind": "field"},
            {"name": "is_active", "type": "boolean", "tag": None, "kind": "field"},
        ],
    }
)

TBI_entities.append(
    {
        "name": "TBI_SdgIndicator_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "target_id", "type": "fk", "tag": "FK", "kind": "fk", "target": "TBI_SdgTarget_2bi", "nullable": False},
            {"name": "code", "type": "string(50)", "tag": None, "kind": "field"},
            {"name": "title", "type": "string(255)", "tag": None, "kind": "field"},
            {"name": "description", "type": "text", "tag": None, "kind": "field"},
            {"name": "tier", "type": "string(50)", "tag": None, "kind": "field"},
            {"name": "is_active", "type": "boolean", "tag": None, "kind": "field"},
        ],
    }
)

TBI_entities.append(
    {
        "name": "TBI_IndicatorSdgLink_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "indicator_id", "type": "fk", "tag": "FK", "kind": "fk", "target": "Indicator", "nullable": False},
            {"name": "sdg_target_id", "type": "fk", "tag": "FK", "kind": "fk", "target": "TBI_SdgTarget_2bi", "nullable": False},
            {"name": "relation_type", "type": "string(50)", "tag": None, "kind": "field"},
            {"name": "confidence", "type": "int", "tag": None, "kind": "field"},
            {"name": "notes", "type": "text", "tag": None, "kind": "field"},
            {"name": "source_url", "type": "string(200)", "tag": None, "kind": "field"},
        ],
    }
)

TBI_entities.append(
    {
        "name": "TBI_MeaConvention_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "code", "type": "string(50)", "tag": None, "kind": "field"},
            {"name": "name", "type": "string(255)", "tag": None, "kind": "field"},
            {"name": "description", "type": "text", "tag": None, "kind": "field"},
            {"name": "url", "type": "string(200)", "tag": None, "kind": "field"},
            {"name": "is_active", "type": "boolean", "tag": None, "kind": "field"},
        ],
    }
)

TBI_entities.append(
    {
        "name": "TBI_MeaReportingTemplate_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "convention_id", "type": "fk", "tag": "FK", "kind": "fk", "target": "TBI_MeaConvention_2bi", "nullable": False},
            {"name": "code", "type": "string(50)", "tag": None, "kind": "field"},
            {"name": "title", "type": "string(255)", "tag": None, "kind": "field"},
            {"name": "version", "type": "string(50)", "tag": None, "kind": "field"},
            {"name": "template_url", "type": "string(200)", "tag": None, "kind": "field"},
            {"name": "is_active", "type": "boolean", "tag": None, "kind": "field"},
        ],
    }
)

TBI_entities.append(
    {
        "name": "TBI_ExternalSystem_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "system_code", "type": "string(50)", "tag": None, "kind": "field"},
            {"name": "name", "type": "string(255)", "tag": None, "kind": "field"},
            {"name": "base_url", "type": "string(200)", "tag": None, "kind": "field"},
            {"name": "contact_email", "type": "string(255)", "tag": None, "kind": "field"},
            {"name": "is_active", "type": "boolean", "tag": None, "kind": "field"},
        ],
    }
)

TBI_entities.append(
    {
        "name": "TBI_ExternalSystemLink_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "external_system_id", "type": "fk", "tag": "FK", "kind": "fk", "target": "TBI_ExternalSystem_2bi", "nullable": False},
            {"name": "entity_type", "type": "string(100)", "tag": None, "kind": "field"},
            {"name": "entity_uuid", "type": "uuid", "tag": None, "kind": "field"},
            {"name": "external_id", "type": "string(255)", "tag": None, "kind": "field"},
            {"name": "external_url", "type": "string(200)", "tag": None, "kind": "field"},
            {"name": "synced_at", "type": "datetime", "tag": None, "kind": "field"},
            {"name": "status", "type": "string(50)", "tag": None, "kind": "field"},
        ],
    }
)

TBI_entities.append(
    {
        "name": "TBI_DataQualityIssue_2bi",
        "fields": [
            {"name": "id", "type": "bigint", "tag": "PK", "kind": "pk"},
            {"name": "subject_type", "type": "string(100)", "tag": None, "kind": "field"},
            {"name": "subject_uuid", "type": "uuid", "tag": None, "kind": "field"},
            {"name": "severity", "type": "string(20)", "tag": None, "kind": "field"},
            {"name": "status", "type": "string(20)", "tag": None, "kind": "field"},
            {"name": "description", "type": "text", "tag": None, "kind": "field"},
            {"name": "detected_at", "type": "datetime", "tag": None, "kind": "field"},
            {"name": "resolved_at", "type": "datetime", "tag": None, "kind": "field"},
            {"name": "detected_by", "type": "fk", "tag": "FK", "kind": "fk", "target": "User", "nullable": True},
            {"name": "notes", "type": "text", "tag": None, "kind": "field"},
        ],
    }
)

TBI_rels = [
    ("TBI_SdgTarget_2bi", "TBI_SdgGoal_2bi", "goal_id", "ForeignKey", False),
    ("TBI_SdgIndicator_2bi", "TBI_SdgTarget_2bi", "target_id", "ForeignKey", False),
    ("TBI_IndicatorSdgLink_2bi", "Indicator", "indicator_id", "ForeignKey", False),
    ("TBI_IndicatorSdgLink_2bi", "TBI_SdgTarget_2bi", "sdg_target_id", "ForeignKey", False),
    ("TBI_MeaReportingTemplate_2bi", "TBI_MeaConvention_2bi", "convention_id", "ForeignKey", False),
    ("TBI_ExternalSystemLink_2bi", "TBI_ExternalSystem_2bi", "external_system_id", "ForeignKey", False),
    ("TBI_DataQualityIssue_2bi", "User", "detected_by", "ForeignKey", True),
]

integration_entities = [
    ("User", "anchor"),
    ("Indicator", "anchor"),
]
render_page(
    "07-INTEGRATION-_2bi",
    "Page-07-INTEGRATION-2BI.mmd",
    integration_entities,
    extra_entities=TBI_entities,
    extra_rels=TBI_rels,
    comments=[
        "TO-BE (_2bi) integration and interoperability tables.",
        "TBI_ prefix denotes proposed tables (documentation-only).",
    ],
)


# --- Write Mermaid files ---
mermaid_dir = Path("docs/erd/mermaid")
mermaid_dir.mkdir(parents=True, exist_ok=True)

for page in pages:
    (mermaid_dir / page["filename"]).write_text(page["mermaid"], encoding="utf-8")


# --- Build draw.io multi-page file ---
def xml_escape_attr(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("\n", "&#xa;")
    )


modified = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

# Page sizes
page_width = 2600
page_height = 1800

mxfile_lines = [f'<mxfile host="app.diagrams.net" modified="{modified}" agent="Codex" version="20.8.16" type="device">']

for page in pages:
    diagram_id = uuid.uuid4().hex[:12]
    mermaid_attr = xml_escape_attr(page["mermaid"])
    mxfile_lines.append(f'  <diagram id="{diagram_id}" name="{page["name"]}">')
    mxfile_lines.append(
        f'    <mxGraphModel dx="1422" dy="794" grid="1" gridSize="10" guides="1" tooltips="1" '
        f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_width}" '
        f'pageHeight="{page_height}" math="0" shadow="0">'
    )
    mxfile_lines.append("      <root>")
    mxfile_lines.append('        <mxCell id="0" />')
    mxfile_lines.append('        <mxCell id="1" parent="0" />')

    # Title
    mxfile_lines.append(
        f'        <mxCell id="2" value="{page["name"]}" '
        f'style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;'
        f'fontSize=16;fontStyle=1" vertex="1" parent="1">'
    )
    mxfile_lines.append('          <mxGeometry x="20" y="20" width="800" height="30" as="geometry" />')
    mxfile_lines.append("        </mxCell>")

    # Mermaid
    mxfile_lines.append(
        f'        <mxCell id="3" value="{mermaid_attr}" '
        f'style="shape=mxgraph.mermaid;whiteSpace=wrap;html=1;" vertex="1" parent="1">'
    )
    mxfile_lines.append(
        f'          <mxGeometry x="20" y="60" width="{page_width - 40}" height="{page_height - 80}" '
        f'as="geometry" />'
    )
    mxfile_lines.append("        </mxCell>")

    mxfile_lines.append("      </root>")
    mxfile_lines.append("    </mxGraphModel>")
    mxfile_lines.append("  </diagram>")

mxfile_lines.append("</mxfile>")

out_path = Path("docs/ops/db_schema_v2.drawio")
out_path.write_text("\n".join(mxfile_lines), encoding="utf-8")

print(str(out_path))
