from sqlalchemy import BigInteger, Column
from sqlalchemy.dialects.postgresql import INET
from sqlmodel import Field, SQLModel


class IpAsnRange(SQLModel, table=True):
    __tablename__ = "ip_asn_ranges"

    start_ip: str = Field(sa_column=Column(INET, primary_key=True))
    end_ip: str = Field(sa_column=Column(INET, nullable=False))
    asn: int = Field(sa_column=Column(BigInteger, nullable=False))
    as_name: str | None = Field(default=None, max_length=255)


class IpCountryRange(SQLModel, table=True):
    __tablename__ = "ip_country_ranges"

    start_ip: str = Field(sa_column=Column(INET, primary_key=True))
    end_ip: str = Field(sa_column=Column(INET, nullable=False))
    country: str = Field(max_length=2)
