from pydantic import BaseModel, Field


class QueryFieldSpec(BaseModel):
    name: str
    type: str
    group: str
    description: str
    example: str
    aliases: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    facet: str | None = None
    operators: list[str] = Field(default_factory=list)
    free_text: bool = False
    unit: str | None = None
    dynamic_sub: str | None = None


class QueryOperatorSpec(BaseModel):
    symbol: str
    description: str


class QueryExampleSpec(BaseModel):
    query: str
    description: str
    group: str = ""
    generic: bool = False


class QueryLead(QueryExampleSpec):
    count: int = 0
    capped: bool = False


class QueryLeads(BaseModel):
    leads: list[QueryLead] = Field(default_factory=list)
    total: int = 0
    total_capped: bool = False
    filtered: bool = False
    computed: bool = False


class QueryGroupSpec(BaseModel):
    key: str
    label: str
    description: str


class QueryGroup(BaseModel):
    value: str
    label: str
    count: int
    query: str


class QueryGroups(BaseModel):
    dimension: str = ""
    groups: list[QueryGroup] = Field(default_factory=list)
    total_groups: int = 0
    truncated: bool = False
    hosts: int = 0
    covered: int = 0


class QueryFlagSpec(BaseModel):
    value: str
    description: str


class QuerySchema(BaseModel):
    max_length: int = 0
    max_terms: int = 0
    groups: list[str] = Field(default_factory=list)
    example_groups: list[str] = Field(default_factory=list)
    group_dimensions: list[QueryGroupSpec] = Field(default_factory=list)
    fields: list[QueryFieldSpec] = Field(default_factory=list)
    operators: list[QueryOperatorSpec] = Field(default_factory=list)
    connectors: list[QueryOperatorSpec] = Field(default_factory=list)
    flags: list[QueryFlagSpec] = Field(default_factory=list)
    examples: list[QueryExampleSpec] = Field(default_factory=list)


class QueryError(BaseModel):
    message: str
    hint: str | None = None
    start: int = 0
    end: int = 0


class MatchEvidence(BaseModel):
    field: str
    label: str
    term: str
    snippet: str | None = None
