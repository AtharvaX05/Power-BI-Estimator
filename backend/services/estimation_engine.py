"""Rule-based Power BI effort estimation engine — v2 (hours-based).

Uses industry-aligned effort benchmarks in HOURS.
Final output includes both hours and days (hours / 8).
"""
from typing import List, Tuple

from backend.models.project import (
    EstimationInput, EstimationOutput, ModuleEffort,
    Complexity, PerformanceLevel,
)

# ── Complexity multipliers (per module) ──────────────────────────

DATA_SOURCE_MULTIPLIER = {Complexity.LOW: 1.0, Complexity.MEDIUM: 1.5, Complexity.HIGH: 2.5}
TRANSFORMATION_MULTIPLIER = {Complexity.LOW: 1.0, Complexity.MEDIUM: 1.75, Complexity.HIGH: 3.0}
MODELING_MULTIPLIER = {Complexity.LOW: 1.0, Complexity.MEDIUM: 1.75, Complexity.HIGH: 3.0}
DAX_MULTIPLIER = {Complexity.LOW: 1.0, Complexity.MEDIUM: 2.0, Complexity.HIGH: 3.5}
REPORT_MULTIPLIER = {Complexity.LOW: 1.0, Complexity.MEDIUM: 1.5, Complexity.HIGH: 2.5}

# ── Fixed effort constants (hours) ───────────────────────────────

HOURS_PER_DATA_SOURCE = 4
HOURS_PER_SOURCE_TRANSFORMATION = 6
HOURS_PER_DATA_MODEL = 8
HOURS_INCREMENTAL_REFRESH = 6       # per model, if enabled
HOURS_DAX_BASE = 10
HOURS_REPORT_INTRO = 2              # landing / intro page per report
HOURS_PER_PAGE = 2
HOURS_FEATURE_TOOLTIPS = 2
HOURS_FEATURE_SUBSCRIPTIONS = 1
HOURS_FEATURE_ALERTS = 1
HOURS_RLS_BASE = 6
HOURS_RLS_FINAL = 12                # doubled
HOURS_PERF_STANDARD = 12
HOURS_PERF_COMPLEX = 20
HOURS_PER_UAT_CYCLE = 16
HOURS_DEPLOYMENT = 8
HOURS_DOCUMENTATION = 4


class EstimationEngine:
    """Stateless rule-based estimation calculator (v2 — hours)."""

    def calculate(self, inp: EstimationInput) -> EstimationOutput:
        modules: List[ModuleEffort] = []
        assumptions: List[str] = []

        # 1. Project Metadata & Scoping
        modules.append(self._project_metadata(inp))
        assumptions.append("Project scoping includes requirement gathering, stakeholder alignment, and project planning.")

        # 2. Data Source Integration
        modules.append(self._data_sources(inp))
        assumptions.append(
            f"{inp.num_data_sources} data source(s) with {inp.data_source_complexity.value} complexity."
        )

        # 3. Data Transformation
        modules.append(self._data_transformation(inp))
        assumptions.append(
            f"{inp.num_data_sources} source(s) requiring {inp.transformation_complexity.value} complexity transformations."
        )

        # 4. Data Modeling
        modules.append(self._data_modeling(inp))
        model_note = f"{inp.num_data_models} data model(s) with {inp.modeling_complexity.value} complexity."
        if inp.incremental_refresh:
            model_note += " Incremental refresh enabled."
        assumptions.append(model_note)

        # 5. DAX / Business Logic
        modules.append(self._dax_logic(inp))
        assumptions.append(
            f"DAX logic with {inp.dax_complexity.value} complexity."
        )

        # 6. Report Development (with optional UI/UX designer 1.2x)
        report_module = self._report_development(inp)
        if inp.ui_ux_designer:
            report_module.computed_effort_hours = round(report_module.computed_effort_hours * 1.2, 1)
        modules.append(report_module)
        feature_parts = []
        if inp.feature_tooltips:
            feature_parts.append("Tooltips")
        if inp.feature_subscriptions:
            feature_parts.append("Subscriptions")
        if inp.feature_alerts:
            feature_parts.append("Alerts")
        feat_str = ", ".join(feature_parts) if feature_parts else "No extra features"
        report_assumption = (
            f"{inp.num_reports} report(s), {inp.pages_per_report} pages each, "
            f"{inp.report_complexity.value} complexity. {feat_str}."
        )
        if inp.ui_ux_designer:
            report_assumption += " UI/UX Designer contribution applied (1.2×)."
        assumptions.append(report_assumption)

        # 7. Security (RLS)
        modules.append(self._security(inp))
        if inp.rls_required:
            assumptions.append("Row-Level Security enabled.")
        else:
            assumptions.append("Row-Level Security not required.")

        # 8. Performance Optimization
        modules.append(self._performance(inp))
        if inp.performance_level == PerformanceLevel.STANDARD:
            assumptions.append("Standard performance optimization included.")
        elif inp.performance_level == PerformanceLevel.COMPLEX:
            assumptions.append("Complex performance optimization included.")
        else:
            assumptions.append("No performance optimization requested.")

        # 9. UAT & Iterations
        modules.append(self._uat(inp))
        assumptions.append(f"{inp.uat_cycles} UAT cycle(s) planned.")

        # 10. Deployment
        modules.append(self._deployment(inp))
        assumptions.append(f"Deployment effort as specified ({inp.deployment_type.value}).")

        # 11. Documentation & Handover
        modules.append(self._documentation(inp))
        if inp.documentation_required:
            assumptions.append("Documentation and handover included.")
        else:
            assumptions.append("Documentation not requested.")

        # Aggregate base hours (11 core modules, before any buffer)
        base_hours = round(sum(m.computed_effort_hours for m in modules), 1)

        # Total buffer = TL% + BA% + Buffer%
        tl_pct = max(0.0, min(inp.tl_percentage, 100.0))
        ba_pct = max(0.0, min(inp.ba_percentage, 100.0))
        buffer_pct = max(0.0, min(inp.buffer_percentage, 100.0))
        total_buffer_pct = tl_pct + ba_pct + buffer_pct

        # For display: TL/BA hours based on base_hours
        tl_hours = round(base_hours * tl_pct / 100, 1)
        ba_hours = round(base_hours * ba_pct / 100, 1)

        # Apply combined buffer per-module: round each individually
        if total_buffer_pct > 0:
            for m in modules:
                m.computed_effort_hours = round(m.computed_effort_hours * (1 + total_buffer_pct / 100))

        # Total = sum of all buffered module hours — do NOT round again
        total_hours = sum(m.computed_effort_hours for m in modules)
        total_days = round(total_hours / 8, 1)

        confidence, reason = self._confidence(inp, total_hours)

        return EstimationOutput(
            total_effort_hours=total_hours,
            total_effort_days=total_days,
            base_effort_hours=base_hours,
            tl_percentage=tl_pct,
            ba_percentage=ba_pct,
            tl_hours=tl_hours,
            ba_hours=ba_hours,
            buffer_percentage=buffer_pct,
            total_buffer_percentage=total_buffer_pct,
            module_breakdown=modules,
            assumptions=assumptions,
            confidence_level=confidence,
            confidence_reason=reason,
        )

    # ── Module calculators ────────────────────────────────────────

    @staticmethod
    def _project_metadata(inp: EstimationInput) -> ModuleEffort:
        """Scoping hours as specified by user."""
        hours = max(0.0, inp.scoping_hours)
        return ModuleEffort(
            module_name="Project Metadata & Scoping",
            base_effort_hours=hours,
            complexity_multiplier=1.0,
            computed_effort_hours=hours,
            notes="Requirement gathering, stakeholder alignment, project planning.",
        )

    @staticmethod
    def _data_sources(inp: EstimationInput) -> ModuleEffort:
        """num_sources × 4h × complexity_multiplier"""
        base = inp.num_data_sources * HOURS_PER_DATA_SOURCE
        mult = DATA_SOURCE_MULTIPLIER[inp.data_source_complexity]
        effort = round(base * mult, 1)
        return ModuleEffort(
            module_name="Data Source Integration",
            base_effort_hours=base,
            complexity_multiplier=mult,
            computed_effort_hours=effort,
            notes=f"{inp.num_data_sources} source(s) × {HOURS_PER_DATA_SOURCE}h × {mult}x",
        )

    @staticmethod
    def _data_transformation(inp: EstimationInput) -> ModuleEffort:
        """num_sources × 6h × complexity_multiplier"""
        base = inp.num_data_sources * HOURS_PER_SOURCE_TRANSFORMATION
        mult = TRANSFORMATION_MULTIPLIER[inp.transformation_complexity]
        effort = round(base * mult, 1)
        return ModuleEffort(
            module_name="Data Transformation (Power Query / ETL)",
            base_effort_hours=base,
            complexity_multiplier=mult,
            computed_effort_hours=effort,
            notes=f"{inp.num_data_sources} source(s) × {HOURS_PER_SOURCE_TRANSFORMATION}h × {mult}x",
        )

    @staticmethod
    def _data_modeling(inp: EstimationInput) -> ModuleEffort:
        """num_models × 8h × complexity  +  incremental_refresh × 6h per model"""
        base = inp.num_data_models * HOURS_PER_DATA_MODEL
        mult = MODELING_MULTIPLIER[inp.modeling_complexity]
        effort = round(base * mult, 1)
        if inp.incremental_refresh:
            effort += inp.num_data_models * HOURS_INCREMENTAL_REFRESH
            effort = round(effort, 1)
        return ModuleEffort(
            module_name="Data Modeling",
            base_effort_hours=base,
            complexity_multiplier=mult,
            computed_effort_hours=effort,
            notes=(
                f"{inp.num_data_models} model(s) × {HOURS_PER_DATA_MODEL}h × {mult}x"
                + (f" + {inp.num_data_models}×{HOURS_INCREMENTAL_REFRESH}h incr. refresh" if inp.incremental_refresh else "")
            ),
        )

    @staticmethod
    def _dax_logic(inp: EstimationInput) -> ModuleEffort:
        """10h base × complexity_multiplier"""
        base = HOURS_DAX_BASE
        mult = DAX_MULTIPLIER[inp.dax_complexity]
        effort = round(base * mult, 1)
        return ModuleEffort(
            module_name="DAX / Business Logic",
            base_effort_hours=base,
            complexity_multiplier=mult,
            computed_effort_hours=effort,
            notes=f"{HOURS_DAX_BASE}h base × {mult}x ({inp.dax_complexity.value})",
        )

    @staticmethod
    def _report_development(inp: EstimationInput) -> ModuleEffort:
        """Per report: 2h intro + (pages × 2h × complexity) + features.  Summed over all reports."""
        mult = REPORT_MULTIPLIER[inp.report_complexity]

        # Feature hours (applied once per report)
        feature_hours = 0.0
        if inp.feature_tooltips:
            feature_hours += HOURS_FEATURE_TOOLTIPS
        if inp.feature_subscriptions:
            feature_hours += HOURS_FEATURE_SUBSCRIPTIONS
        if inp.feature_alerts:
            feature_hours += HOURS_FEATURE_ALERTS

        per_report = HOURS_REPORT_INTRO + (inp.pages_per_report * HOURS_PER_PAGE * mult) + feature_hours
        total = round(inp.num_reports * per_report, 1)
        base_raw = round(inp.num_reports * (HOURS_REPORT_INTRO + inp.pages_per_report * HOURS_PER_PAGE + feature_hours), 1)

        return ModuleEffort(
            module_name="Report Development (UI/UX)",
            base_effort_hours=base_raw,
            complexity_multiplier=mult,
            computed_effort_hours=total,
            notes=(
                f"{inp.num_reports} report(s) × (2h intro + {inp.pages_per_report}pg × 2h × {mult}x"
                + (f" + {feature_hours}h features" if feature_hours else "")
                + ")"
            ),
        )

    @staticmethod
    def _security(inp: EstimationInput) -> ModuleEffort:
        """RLS: base 6h → final 12h (doubled). Or 0 if not required."""
        if not inp.rls_required:
            return ModuleEffort(
                module_name="Security (RLS)",
                base_effort_hours=0, complexity_multiplier=1.0,
                computed_effort_hours=0, notes="RLS not required.",
            )
        return ModuleEffort(
            module_name="Security (RLS)",
            base_effort_hours=HOURS_RLS_BASE,
            complexity_multiplier=2.0,
            computed_effort_hours=HOURS_RLS_FINAL,
            notes=f"Base {HOURS_RLS_BASE}h → final {HOURS_RLS_FINAL}h (doubled).",
        )

    @staticmethod
    def _performance(inp: EstimationInput) -> ModuleEffort:
        """Standard: 12h, Complex: 20h, None: 0h."""
        if inp.performance_level == PerformanceLevel.STANDARD:
            return ModuleEffort(
                module_name="Performance Optimization",
                base_effort_hours=HOURS_PERF_STANDARD, complexity_multiplier=1.0,
                computed_effort_hours=HOURS_PERF_STANDARD,
                notes="Standard optimization (query folding, aggregations).",
            )
        elif inp.performance_level == PerformanceLevel.COMPLEX:
            return ModuleEffort(
                module_name="Performance Optimization",
                base_effort_hours=HOURS_PERF_COMPLEX, complexity_multiplier=1.0,
                computed_effort_hours=HOURS_PERF_COMPLEX,
                notes="Complex optimization (composite models, partitions, tuning).",
            )
        return ModuleEffort(
            module_name="Performance Optimization",
            base_effort_hours=0, complexity_multiplier=1.0,
            computed_effort_hours=0, notes="Not requested.",
        )

    @staticmethod
    def _uat(inp: EstimationInput) -> ModuleEffort:
        """16h per UAT cycle."""
        base = inp.uat_cycles * HOURS_PER_UAT_CYCLE
        return ModuleEffort(
            module_name="UAT & Iterations",
            base_effort_hours=base, complexity_multiplier=1.0,
            computed_effort_hours=base,
            notes=f"{inp.uat_cycles} cycle(s) × {HOURS_PER_UAT_CYCLE}h",
        )

    @staticmethod
    def _deployment(inp: EstimationInput) -> ModuleEffort:
        """Deployment hours as specified by user."""
        hours = max(0.0, inp.deployment_hours)
        return ModuleEffort(
            module_name="Deployment",
            base_effort_hours=hours, complexity_multiplier=1.0,
            computed_effort_hours=hours,
            notes=f"Deployment: {inp.deployment_type.value}.",
        )

    @staticmethod
    def _documentation(inp: EstimationInput) -> ModuleEffort:
        """4h for documentation & handover."""
        if not inp.documentation_required:
            return ModuleEffort(
                module_name="Documentation & Handover",
                base_effort_hours=0, complexity_multiplier=1.0,
                computed_effort_hours=0, notes="Not requested.",
            )
        return ModuleEffort(
            module_name="Documentation & Handover",
            base_effort_hours=HOURS_DOCUMENTATION, complexity_multiplier=1.0,
            computed_effort_hours=HOURS_DOCUMENTATION,
            notes="Technical docs, user guide, handover sessions.",
        )

    # ── Confidence heuristic ──────────────────────────────────────

    @staticmethod
    def _confidence(inp: EstimationInput, total_hours: float) -> Tuple[str, str]:
        score = 0
        reasons = []

        if inp.num_data_sources >= 1:
            score += 1
        if inp.num_tables >= 1:
            score += 1
        if inp.num_reports >= 1:
            score += 1
        if inp.num_measures >= 1:
            score += 1
        if inp.uat_cycles >= 1:
            score += 1

        if total_hours < 20:
            reasons.append("Total effort very low — inputs may be incomplete.")
        elif total_hours > 800:
            reasons.append("Large project — consider breaking into phases.")

        if score >= 4:
            level = "High"
            reasons.append("Most input parameters provided.")
        elif score >= 2:
            level = "Medium"
            reasons.append("Some input parameters may need refinement.")
        else:
            level = "Low"
            reasons.append("Limited inputs — estimate is rough.")

        return level, " ".join(reasons)

