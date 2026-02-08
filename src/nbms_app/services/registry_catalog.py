from __future__ import annotations

from dataclasses import dataclass


GET_REFERENCE_ROWS = [
    {"code": "L1-Terrestrial", "level": 1, "label": "Terrestrial", "parent": "", "description": "Global realm"},
    {"code": "L1-Freshwater", "level": 1, "label": "Freshwater", "parent": "", "description": "Global realm"},
    {"code": "L1-Marine", "level": 1, "label": "Marine", "parent": "", "description": "Global realm"},
    {"code": "L2-Temperate", "level": 2, "label": "Temperate", "parent": "L1-Terrestrial", "description": ""},
    {"code": "L2-Tropical", "level": 2, "label": "Tropical", "parent": "L1-Terrestrial", "description": ""},
    {"code": "L3-Grassland", "level": 3, "label": "Grassland and savanna", "parent": "L2-Temperate", "description": ""},
    {"code": "L3-Forest", "level": 3, "label": "Forest and woodland", "parent": "L2-Temperate", "description": ""},
    {"code": "L4-SouthAfricaSavanna", "level": 4, "label": "South African savanna", "parent": "L3-Grassland", "description": ""},
    {"code": "L4-SouthAfricaGrassland", "level": 4, "label": "South African grassland", "parent": "L3-Grassland", "description": ""},
    {"code": "L5-VegMapSubtype", "level": 5, "label": "VegMap subtype", "parent": "L4-SouthAfricaSavanna", "description": ""},
    {"code": "L6-NationalType", "level": 6, "label": "National ecosystem type", "parent": "L5-VegMapSubtype", "description": ""},
]


@dataclass(frozen=True)
class ProgrammeTemplateDefinition:
    template_code: str
    title: str
    domain: str
    description: str
    pipeline_definition_json: dict
    required_outputs_json: list[dict]


PROGRAMME_TEMPLATE_DEFINITIONS = [
    ProgrammeTemplateDefinition(
        template_code="NBMS-PROG-ECOSYSTEMS",
        title="NBMS Ecosystems Programme",
        domain="ecosystems",
        description="VegMap baseline, ecosystem crosswalk review, and extent/protection overlays.",
        pipeline_definition_json={
            "steps": [
                {"key": "ingest_vegmap_baseline", "type": "ingest"},
                {"key": "validate_ecosystem_registry", "type": "validate"},
                {"key": "compute_ecosystem_outputs", "type": "compute"},
                {"key": "publish_ecosystem_outputs", "type": "publish"},
            ]
        },
        required_outputs_json=[
            {"code": "ecosystem_registry", "label": "Ecosystem registry table"},
            {"code": "rle_assessment_summary", "label": "RLE-ready assessment summary"},
        ],
    ),
    ProgrammeTemplateDefinition(
        template_code="NBMS-PROG-TAXA",
        title="NBMS Taxa Programme",
        domain="taxa",
        description="Taxonomic backbone, source reconciliation, voucher coverage and occurrence readiness.",
        pipeline_definition_json={
            "steps": [
                {"key": "ingest_taxon_backbone", "type": "ingest"},
                {"key": "validate_taxon_records", "type": "validate"},
                {"key": "compute_taxon_readiness", "type": "compute"},
                {"key": "publish_taxon_outputs", "type": "publish"},
            ]
        },
        required_outputs_json=[
            {"code": "taxon_backbone", "label": "Taxon concept backbone"},
            {"code": "voucher_readiness", "label": "Voucher readiness summary"},
        ],
    ),
    ProgrammeTemplateDefinition(
        template_code="NBMS-PROG-IAS",
        title="NBMS IAS Programme",
        domain="ias",
        description="GRIIS baseline ingest and EICAT/SEICAT assessment workflows.",
        pipeline_definition_json={
            "steps": [
                {"key": "ingest_griis_baseline", "type": "ingest"},
                {"key": "validate_ias_profiles", "type": "validate"},
                {"key": "compute_ias_readiness", "type": "compute"},
                {"key": "publish_ias_outputs", "type": "publish"},
            ]
        },
        required_outputs_json=[
            {"code": "ias_baseline", "label": "IAS checklist baseline"},
            {"code": "eicat_seicat_summary", "label": "Impact assessment summary"},
        ],
    ),
    ProgrammeTemplateDefinition(
        template_code="NBMS-PROG-PROTECTED-AREAS",
        title="NBMS Protected Areas Programme",
        domain="protected_areas",
        description="Protected areas spatial pipeline linked to national reporting products.",
        pipeline_definition_json={
            "steps": [
                {"key": "ingest_pa_layers", "type": "ingest"},
                {"key": "validate_pa_layers", "type": "validate"},
                {"key": "compute_pa_coverage", "type": "compute"},
                {"key": "publish_pa_outputs", "type": "publish"},
            ]
        },
        required_outputs_json=[
            {"code": "pa_boundaries", "label": "Protected area boundaries"},
            {"code": "pa_coverage_stats", "label": "Protected area coverage metrics"},
        ],
    ),
]


TAXON_DEMO_ROWS = [
    {"taxon_code": "ZA-TAX-0001", "scientific_name": "Panthera leo", "rank": "species", "kingdom": "Animalia", "phylum": "Chordata", "class": "Mammalia", "order": "Carnivora", "family": "Felidae", "genus": "Panthera", "species": "leo", "is_native": True, "is_endemic": False},
    {"taxon_code": "ZA-TAX-0002", "scientific_name": "Aloe ferox", "rank": "species", "kingdom": "Plantae", "phylum": "Tracheophyta", "class": "Magnoliopsida", "order": "Asparagales", "family": "Asphodelaceae", "genus": "Aloe", "species": "ferox", "is_native": True, "is_endemic": True},
    {"taxon_code": "ZA-TAX-0003", "scientific_name": "Spheniscus demersus", "rank": "species", "kingdom": "Animalia", "phylum": "Chordata", "class": "Aves", "order": "Sphenisciformes", "family": "Spheniscidae", "genus": "Spheniscus", "species": "demersus", "is_native": True, "is_endemic": False},
    {"taxon_code": "ZA-TAX-0004", "scientific_name": "Acacia mearnsii", "rank": "species", "kingdom": "Plantae", "phylum": "Tracheophyta", "class": "Magnoliopsida", "order": "Fabales", "family": "Fabaceae", "genus": "Acacia", "species": "mearnsii", "is_native": False, "is_endemic": False},
]


IAS_DEMO_ROWS = [
    {
        "scientific_name": "Acacia mearnsii",
        "country_code": "ZA",
        "source_identifier": "GRIIS-ZA-0001",
        "is_alien": True,
        "is_invasive": True,
        "establishment_means_code": "introduced",
        "degree_of_establishment_code": "invasive",
        "pathway_code": "escape",
    },
    {
        "scientific_name": "Opuntia ficus-indica",
        "country_code": "ZA",
        "source_identifier": "GRIIS-ZA-0002",
        "is_alien": True,
        "is_invasive": True,
        "establishment_means_code": "introduced",
        "degree_of_establishment_code": "naturalised",
        "pathway_code": "release",
    },
]
