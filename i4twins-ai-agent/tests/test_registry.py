import pytest
from pydantic import ValidationError

from app.graph import build_graph
from app.main import run_request
from app.skills import build_default_registry, discover_builtin_skills
from app.skills.base import Skill, SkillContext, SkillMetadata
from app.skills.registry import RegistryError, SkillRegistry
from tests.conftest import FakeLLM, route_json


def make_metadata(skill_id="currency_converter", **overrides) -> SkillMetadata:
    data = dict(
        id=skill_id, name="Currency Converter",
        description="Converts an amount of money from one currency to another.",
        input_types=["text"], operations=["convert"],
        routing_examples=["Convert 100 USD to EUR"], keywords=[r"currency", r"convert"],
    )
    return SkillMetadata(**{**data, **overrides})


def make_skill(skill_id="currency_converter", reply="42 EUR", **overrides) -> Skill:
    return Skill(make_metadata(skill_id, **overrides), lambda ctx: reply)


# ------------------------------------------------------------------ the four real skills
def test_default_registry_has_exactly_the_four_required_skills():
    registry = build_default_registry()
    assert sorted(registry.ids()) == ["calculator", "general_chat", "summarizer", "translator"]
    assert len(discover_builtin_skills()) == 4
    assert registry.fallback().id == "general_chat"


def test_every_skill_has_complete_metadata():
    for meta in build_default_registry().metadata():
        assert meta.name and meta.description and meta.input_types and meta.operations
        assert meta.routing_examples and len(meta.description) <= 200


def test_registry_exposes_metadata_without_prompts():
    for meta in build_default_registry().metadata():
        assert "ROLE:" not in meta.model_dump_json()      # no full prompt text in routing metadata


# ------------------------------------------------------------------ registering new skills
def test_new_skill_is_registered_and_discovered():
    registry = build_default_registry()
    registry.register(make_skill())
    assert len(registry) == 5 and "currency_converter" in registry
    assert registry.get("currency_converter").metadata.name == "Currency Converter"


def test_new_skill_works_end_to_end_without_touching_router_or_graph(make_graph_with_registry):
    registry = build_default_registry()
    registry.register(make_skill(reply="100 USD = 92 EUR"))
    graph, llm = make_graph_with_registry(registry, router=route_json(["currency_converter"]))
    state = run_request(graph, "Convert 100 USD to EUR")
    assert state.final_response == "100 USD = 92 EUR"
    assert "id=currency_converter" in llm.system_for("router")      # router discovered it via metadata


def test_new_skill_can_chain_with_an_existing_one(make_graph_with_registry):
    registry = build_default_registry()
    registry.register(make_skill(accepts_previous_output=True, reply="converted"))
    graph, llm = make_graph_with_registry(
        registry, router=route_json(["currency_converter", "translator"], dependent=True), translator="تبدیل شد")
    state = run_request(graph, "Convert 100 USD to EUR then translate it")
    assert llm.roles() == ["router", "translator"] and "converted" in llm.user_for("translator")
    assert state.final_response == "تبدیل شد"


def test_duplicate_skill_ids_are_rejected():
    registry = build_default_registry()
    with pytest.raises(RegistryError, match="duplicate skill id 'translator'"):
        registry.register(make_skill("translator"))


def test_only_one_fallback_skill_is_allowed():
    registry = build_default_registry()
    with pytest.raises(RegistryError, match="only one fallback"):
        registry.register(make_skill("another_chat", is_fallback=True))


def test_registering_a_non_skill_is_rejected():
    with pytest.raises(RegistryError, match="expected a Skill"):
        SkillRegistry().register("translator")            # type: ignore[arg-type]


def test_unknown_skill_lookup_raises():
    with pytest.raises(RegistryError, match="unknown skill id 'poet'"):
        build_default_registry().get("poet")


@pytest.mark.parametrize("overrides", [
    dict(skill_id="Bad-Id"),                                  # not snake_case
    dict(skill_id="x"),                                       # too short
    dict(description="short"),                                # description too short
    dict(description="x" * 201),                              # too long for compact routing metadata
    dict(input_types=[]),
    dict(operations=[]),
    dict(routing_examples=[]),
    dict(routing_examples=["a"] * 5),
    dict(routing_examples=["x" * 121]),
    dict(keywords=["(unclosed"]),                             # invalid regex
    dict(requires_content=True),                              # needs missing_input_question
    dict(is_fallback=True, requires_content=True, missing_input_question={"en": "?"}),
    dict(name=""),
])
def test_invalid_metadata_is_rejected(overrides):
    skill_id = overrides.pop("skill_id", "currency_converter")
    with pytest.raises(ValidationError):
        make_metadata(skill_id, **overrides)


def test_unknown_metadata_fields_are_rejected():
    with pytest.raises(ValidationError):
        make_metadata(prompt="a full prompt must not live in routing metadata")


def test_non_callable_handler_is_rejected():
    with pytest.raises(TypeError, match="callable"):
        Skill(make_metadata(), "not a function")           # type: ignore[arg-type]


def test_skill_runs_through_its_handler():
    skill = make_skill(reply="ok")
    assert skill.run(SkillContext(FakeLLM(), "x")) == "ok"


@pytest.fixture
def make_graph_with_registry():
    def _make(registry, **replies):
        llm = FakeLLM(**replies)
        return build_graph(llm, registry), llm
    return _make
