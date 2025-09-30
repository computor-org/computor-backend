from sqlalchemy import Column, String, CheckConstraint
from sqlalchemy.orm import relationship
from .base import Base


class Language(Base):
    """Language model for ISO 639-1 language codes.

    Used for course default language and user language preferences.
    Determines which README_<language_code>.md file is used in VSCode extension.
    """
    __tablename__ = 'language'
    __table_args__ = (
        CheckConstraint("length(code) = 2", name='ck_language_code_length'),
        CheckConstraint("code ~ '^[a-z]{2}$'", name='ck_language_code_format'),
    )

    code = Column(String(2), primary_key=True)
    name = Column(String(255), nullable=False)
    native_name = Column(String(255))

    # Relationships
    profiles = relationship('Profile', back_populates='language')
    courses = relationship('Course', back_populates='language')