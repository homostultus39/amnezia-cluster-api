from pydantic import BaseModel, Field, field_validator


class JunkPacketConfig(BaseModel):
    jc: int = Field(default=4, ge=0, le=10)
    jmin: int = Field(default=50, ge=0)
    jmax: int = Field(default=1000, ge=50)
    s1: int = Field(default=0, ge=0)
    s2: int = Field(default=0, ge=0)
    s3: int = Field(default=0, ge=0)
    s4: int = Field(default=0, ge=0)
    h1: int = Field(default=1, ge=0)
    h2: int = Field(default=2, ge=0)
    h3: int = Field(default=3, ge=0)
    h4: int = Field(default=4, ge=0)
    i1: int = Field(default=0, ge=0)
    i2: int = Field(default=0, ge=0)
    i3: int = Field(default=0, ge=0)
    i4: int = Field(default=0, ge=0)
    i5: int = Field(default=0, ge=0)

    @field_validator("jmax")
    @classmethod
    def validate_jmax(cls, v: int, info) -> int:
        jmin = info.data.get("jmin", 50)
        if v < jmin:
            raise ValueError(f"jmax ({v}) must be >= jmin ({jmin})")
        return v
