import pytz
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Union
from datetime import datetime
import shutil
import threading
import time
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DATABASE_URL = "postgresql://postgres:12345@localhost:5432/tgfrontbrusnika"
DATABASE_URL = "postgresql://postgres:qwerty22375638@localhost:5432/tgfrontbrusnika"
Base = declarative_base()

# Database models
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    organization = Column(String, index=True)
    is_general_contractor = Column(Boolean, default=False)
    work_types_ids = Column(JSON, nullable=True, default=list)  # Добавляем новое поле
    object_ids = Column(JSON, nullable=True, default=list)
    factory = Column(Boolean, default=False)  # Добавлено поле factory


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, unique=True, index=True)
    full_name = Column(String)
    is_authorized = Column(Boolean, default=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True)  # Добавлено поле


    organization = relationship("Organization", back_populates="users")
    object = relationship("Object")  # Добавлено отношение


Organization.users = relationship("User", order_by=User.id, back_populates="organization")


class WorkType(Base):
    __tablename__ = "worktypes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


class Object(Base):
    __tablename__ = "objects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    work_types_ids = Column(JSON, nullable=True, default=list)  # Добавляем новое поле


class BlockSection(Base):
    __tablename__ = "blocksections"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"))
    name = Column(String, index=True)
    number_of_floors = Column(Integer)

    object = relationship("Object", back_populates="block_sections")


Object.block_sections = relationship("BlockSection", order_by=BlockSection.id, back_populates="object")


class FrontTransfer(Base):
    __tablename__ = "fronttransfers"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    object_id = Column(Integer, ForeignKey("objects.id"))
    work_type_id = Column(Integer, ForeignKey("worktypes.id"))
    block_section_id = Column(Integer, ForeignKey("blocksections.id"))
    floor = Column(String)
    status = Column(String)
    photo1 = Column(String, nullable=True)
    photo2 = Column(String, nullable=True)
    photo3 = Column(String, nullable=True)
    photo4 = Column(String, nullable=True)
    photo5 = Column(String, nullable=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    remarks = Column(String, nullable=True)
    next_work_type_id = Column(Integer, ForeignKey("worktypes.id"), nullable=True)
    boss_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approval_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    photo_ids = Column(JSON, nullable=True, default=list)
    sender_chat_id = Column(String)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_transfers")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_transfers")
    next_work_type = relationship("WorkType", foreign_keys=[next_work_type_id])
    boss = relationship("User", foreign_keys=[boss_id])


User.sent_transfers = relationship("FrontTransfer", foreign_keys=[FrontTransfer.sender_id], back_populates="sender")
User.received_transfers = relationship("FrontTransfer", foreign_keys=[FrontTransfer.receiver_id], back_populates="receiver")


class FrontWorkforce(Base):
    __tablename__ = "frontworkforces"

    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"))
    block_section_id = Column(Integer, ForeignKey("blocksections.id"))
    floor = Column(String)
    work_type_id = Column(Integer, ForeignKey("worktypes.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    workforce_count = Column(Integer)
    date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    object = relationship("Object")
    block_section = relationship("BlockSection")
    work_type = relationship("WorkType")
    organization = relationship("Organization")
    user = relationship("User")



class Volume(Base):
    __tablename__ = "volumes"

    id = Column(Integer, primary_key=True, index=True)
    work_type_id = Column(Integer, ForeignKey("worktypes.id"), nullable=True)
    volume = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    date = Column(DateTime, default=datetime.utcnow)  # Добавляем поле с датой
    object_id = Column(Integer, ForeignKey("objects.id"))  # Добавляем поле object_id
    organization_id = Column(Integer, ForeignKey("organizations.id"))  # Добавляем поле organization_id
    block_section_id = Column(Integer, ForeignKey("blocksections.id"))  # Добавляем поле block_section_id
    floor = Column(String)  # Добавляем поле floor

    work_type = relationship("WorkType")
    user = relationship("User")
    object = relationship("Object")
    organization = relationship("Organization")
    block_section = relationship("BlockSection")


class PrefabType(Base):
    __tablename__ = "prefab_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)


class Prefab(Base):
    __tablename__ = "prefabs"

    id = Column(Integer, primary_key=True, index=True)
    prefab_type_id = Column(Integer, ForeignKey("prefab_types.id"), nullable=False)
    prefab_subtype_id = Column(Integer, ForeignKey("prefab_subtypes.id"), nullable=False)
    planned_delivery_date = Column(DateTime, nullable=False)
    actual_delivery_date = Column(DateTime, nullable=True)
    deficit = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    comment = Column(String, nullable=True)

    prefab_type = relationship("PrefabType")
    prefab_subtype = relationship("PrefabSubtype")
    object = relationship("Object")
    organization = relationship("Organization")

class PrefabSubtype(Base):
    __tablename__ = "prefab_subtypes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    prefabtype_id = Column(Integer, ForeignKey("prefab_types.id"), nullable=False)

    prefab_type = relationship("PrefabType")

class PrefabsInWork(Base):
    __tablename__ = "prefabs_in_work"

    id = Column(Integer, primary_key=True, index=True)
    prefab_id = Column(Integer, ForeignKey("prefabs.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String)
    production_date = Column(DateTime, nullable=True)  # Дата производства
    sgp_date = Column(DateTime, nullable=True)         # Дата СГП
    shipping_date = Column(DateTime, nullable=True)    # Дата отгрузки
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)  # Добавлено поле warehouse_id
    photos = Column(JSON, nullable=True, default=list)  # Добавлено поле photos
    comments = Column(String, nullable=True)  # Поле для комментариев
    block_section_id = Column(Integer, ForeignKey("blocksections.id"), nullable=True)  # Добавлено поле block_section_id
    floor = Column(String, nullable=True)  # Добавлено поле floor

    prefab = relationship("Prefab")
    warehouse = relationship("Warehouse", back_populates="prefabs_in_work")
    block_section = relationship("BlockSection")



class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    prefabs_in_work = relationship("PrefabsInWork", back_populates="warehouse")



MOSCOW_TZ = pytz.timezone('Europe/Moscow')

def get_moscow_time():
    return datetime.now(MOSCOW_TZ)
class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=True)
    respondent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="open")
    photo_ids = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), default=get_moscow_time)

# Pydantic models
class OrganizationBase(BaseModel):
    organization: str
    is_general_contractor: bool
    work_types_ids: Optional[List[int]] = Field(default_factory=list)  # Добавляем новое поле
    object_ids: Optional[List[int]] = Field(default_factory=list)
    factory: bool

class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: int

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    chat_id: Union[str, int]
    full_name: str
    is_authorized: bool
    organization_id: Optional[int] = None
    object_id: Optional[int] = None


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    pass


class UserResponse(UserBase):
    id: int

    class Config:
        from_attributes = True


class WorkTypeBase(BaseModel):
    name: str


class WorkTypeCreate(WorkTypeBase):
    pass


class WorkTypeUpdate(WorkTypeBase):
    pass


class WorkTypeResponse(WorkTypeBase):
    id: int

    class Config:
        from_attributes = True


class ObjectBase(BaseModel):
    name: str
    work_types_ids: Optional[List[int]] = Field(default_factory=list)  # Добавляем новое поле



class ObjectCreate(ObjectBase):
    pass


class ObjectUpdate(ObjectBase):
    pass


class ObjectResponse(ObjectBase):
    id: int

    class Config:
        from_attributes = True


class BlockSectionBase(BaseModel):
    object_id: int
    name: str
    number_of_floors: int


class BlockSectionCreate(BlockSectionBase):
    pass


class BlockSectionUpdate(BlockSectionBase):
    pass


class BlockSectionResponse(BlockSectionBase):
    id: int

    class Config:
        from_attributes = True


class FrontTransferBase(BaseModel):
    sender_id: int
    object_id: int
    work_type_id: int
    block_section_id: int
    floor: str
    status: str
    photo1: Optional[str] = None
    photo2: Optional[str] = None
    photo3: Optional[str] = None
    photo4: Optional[str] = None
    photo5: Optional[str] = None
    receiver_id: Optional[int] = None
    remarks: Optional[str] = None
    next_work_type_id: Optional[int] = None
    boss_id: Optional[int] = None
    created_at: datetime
    approval_at: Optional[datetime] = None
    photo_ids: Optional[List[str]] = Field(default_factory=list)
    sender_chat_id: str


class FrontTransferCreate(FrontTransferBase):
    pass


class FrontTransferUpdate(FrontTransferBase):
    pass


class FrontTransferResponse(FrontTransferBase):
    id: int

    class Config:
        from_attributes = True


class FrontWorkforceBase(BaseModel):
    object_id: int
    block_section_id: int
    floor: str
    work_type_id: int
    organization_id: int
    workforce_count: Optional[int] = None
    date: datetime
    user_id: Optional[int] = None

    class Config:
        from_attributes = True


class FrontWorkforceCreate(FrontWorkforceBase):
    pass


class FrontWorkforceUpdate(FrontWorkforceBase):
    pass


class FrontWorkforceResponse(FrontWorkforceBase):
    id: int

    class Config:
        from_attributes = True



class VolumeBase(BaseModel):
    work_type_id: Optional[int] = None
    volume: Optional[int] = None
    user_id: Optional[int] = None
    date: Optional[datetime] = None  # Добавляем поле с датой
    object_id: Optional[int] = None  # Добавляем поле object_id
    organization_id: Optional[int] = None  # Добавляем поле organization_id
    block_section_id: Optional[int] = None  # Добавляем поле block_section_id
    floor: Optional[str] = None  # Добавляем поле floor

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True


class VolumeCreate(VolumeBase):
    pass


class VolumeUpdate(VolumeBase):
    pass


class VolumeResponse(VolumeBase):
    id: int

    class Config:
        from_attributes = True


class PrefabTypeBase(BaseModel):
    name: str


class PrefabTypeCreate(PrefabTypeBase):
    pass


class PrefabTypeUpdate(PrefabTypeBase):
    pass


class PrefabTypeResponse(PrefabTypeBase):
    id: int

    class Config:
        from_attributes = True


class PrefabBase(BaseModel):
    prefab_type_id: int
    prefab_subtype_id: int
    planned_delivery_date: datetime
    actual_delivery_date: Optional[datetime] = None
    deficit: Optional[str] = None
    quantity: int
    object_id: Optional[int] = None
    organization_id: Optional[int] = None
    comment: Optional[str] = None


class PrefabCreate(PrefabBase):
    pass


class PrefabUpdate(PrefabBase):
    pass


class PrefabResponse(PrefabBase):
    id: int

    class Config:
        from_attributes = True


class PrefabSubtypeBase(BaseModel):
    name: str
    prefabtype_id: int


class PrefabSubtypeCreate(PrefabSubtypeBase):
    pass


class PrefabSubtypeUpdate(PrefabSubtypeBase):
    pass


class PrefabSubtypeResponse(PrefabSubtypeBase):
    id: int

    class Config:
        from_attributes = True


class PrefabsInWorkBase(BaseModel):
    prefab_id: int
    quantity: int
    status: str
    production_date: Optional[datetime] = None  # Дата производства
    sgp_date: Optional[datetime] = None         # Дата СГП
    shipping_date: Optional[datetime] = None    # Дата отгрузки
    warehouse_id: Optional[int] = None  # Добавлено поле warehouse_id
    photos: Optional[List[str]] = Field(default_factory=list)  # Добавлено поле photos
    comments: Optional[str] = None
    block_section_id: Optional[int] = None
    floor: Optional[str] = None

class PrefabsInWorkCreate(PrefabsInWorkBase):
    pass

class PrefabsInWorkUpdate(BaseModel):
    quantity: Optional[int] = None  # Добавлено поле quantity
    status: Optional[str] = None
    production_date: Optional[datetime] = None  # Дата производства
    sgp_date: Optional[datetime] = None         # Дата СГП
    shipping_date: Optional[datetime] = None    # Дата отгрузки
    warehouse_id: Optional[int] = None  # Добавлено поле warehouse_id
    photos: Optional[List[str]] = Field(default_factory=list)  # Добавлено поле photos
    comments: Optional[str] = None
    block_section_id: Optional[int] = None
    floor: Optional[str] = None

    class Config:
        from_attributes = True

class PrefabsInWorkResponse(PrefabsInWorkBase):
    id: int

    class Config:
        from_attributes = True





class WarehouseBase(BaseModel):
    name: str


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(WarehouseBase):
    pass


class WarehouseResponse(WarehouseBase):
    id: int

    class Config:
        from_attributes = True



class SupportTicketBase(BaseModel):
    sender_id: int
    question: str
    answer: Optional[str] = None
    respondent_id: Optional[int] = None
    status: Optional[str] = "open"
    photo_ids: Optional[List[str]] = []


class SupportTicketCreate(SupportTicketBase):
    pass

class SupportTicketUpdate(BaseModel):
    answer: Optional[str] = None
    respondent_id: Optional[int] = None
    status: Optional[str] = None
    photo_ids: Optional[List[str]] = None

    class Config:
        from_attributes = True


class SupportTicketResponse(SupportTicketBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# FastAPI setup
app = FastAPI()

# Database session
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=86400, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ping database function
@app.on_event("startup")
async def startup():
    logger.info("Connecting to database...")
    try:
        with engine.connect() as connection:
            logger.info("Database connected!")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Disconnecting from database...")
    try:
        engine.dispose()
        logger.info("Database disconnected!")
    except Exception as e:
        logger.error(f"Failed to disconnect from database: {e}")

# Ping database function
def ping_db():
    while True:
        try:
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                result.close()
            logger.info("Database ping successful")
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
        time.sleep(3600)

# Запуск пингера в отдельном потоке при старте приложения
threading.Thread(target=ping_db, daemon=True).start()



# CRUD operations
def get_organization(db: Session, organization_id: int):
    return db.query(Organization).filter(Organization.id == organization_id).first()


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_chat_id(db: Session, chat_id: Union[str, int]):
    return db.query(User).filter(User.chat_id == str(chat_id)).first()


def get_work_type(db: Session, work_type_id: int):
    return db.query(WorkType).filter(WorkType.id == work_type_id).first()


def get_object(db: Session, object_id: int):
    return db.query(Object).filter(Object.id == object_id).first()


def get_block_section(db: Session, block_section_id: int):
    return db.query(BlockSection).filter(BlockSection.id == block_section_id).first()


def get_front_transfer(db: Session, front_transfer_id: int):
    return db.query(FrontTransfer).filter(FrontTransfer.id == front_transfer_id).first()

def get_volume(db: Session, volume_id: int):
    return db.query(Volume).filter(Volume.id == volume_id).first()

def get_prefab_type(db: Session, prefab_type_id: int):
    return db.query(PrefabType).filter(PrefabType.id == prefab_type_id).first()


def create_prefab_type(db: Session, prefab_type: PrefabTypeCreate):
    db_prefab_type = PrefabType(**prefab_type.dict())
    db.add(db_prefab_type)
    db.commit()
    db.refresh(db_prefab_type)
    return db_prefab_type


def update_prefab_type(db: Session, prefab_type_id: int, prefab_type: PrefabTypeUpdate):
    db_prefab_type = get_prefab_type(db, prefab_type_id)
    if not db_prefab_type:
        raise HTTPException(status_code=404, detail="PrefabType not found")
    for key, value in prefab_type.dict().items():
        setattr(db_prefab_type, key, value)
    db.commit()
    db.refresh(db_prefab_type)
    return db_prefab_type


def delete_prefab_type(db: Session, prefab_type_id: int):
    db_prefab_type = get_prefab_type(db, prefab_type_id)
    if not db_prefab_type:
        raise HTTPException(status_code=404, detail="PrefabType not found")
    db.delete(db_prefab_type)
    db.commit()
    return db_prefab_type


def get_prefab(db: Session, prefab_id: int):
    return db.query(Prefab).filter(Prefab.id == prefab_id).first()


def create_prefab(db: Session, prefab: PrefabCreate):
    db_prefab = Prefab(**prefab.dict())
    db.add(db_prefab)
    db.commit()
    db.refresh(db_prefab)
    return db_prefab


def update_prefab(db: Session, prefab_id: int, prefab: PrefabUpdate):
    db_prefab = get_prefab(db, prefab_id)
    if not db_prefab:
        raise HTTPException(status_code=404, detail="Prefab not found")
    for key, value in prefab.dict().items():
        setattr(db_prefab, key, value)
    db.commit()
    db.refresh(db_prefab)
    return db_prefab


def delete_prefab(db: Session, prefab_id: int):
    db_prefab = get_prefab(db, prefab_id)
    if not db_prefab:
        raise HTTPException(status_code=404, detail="Prefab not found")
    db.delete(db_prefab)
    db.commit()
    return db_prefab

def get_prefabs_in_work(db: Session, prefabs_in_work_id: int):
    return db.query(PrefabsInWork).filter(PrefabsInWork.id == prefabs_in_work_id).first()

def create_prefabs_in_work(db: Session, prefabs_in_work: PrefabsInWorkCreate):
    db_prefabs_in_work = PrefabsInWork(**prefabs_in_work.dict())
    db.add(db_prefabs_in_work)
    db.commit()
    db.refresh(db_prefabs_in_work)
    return db_prefabs_in_work

def update_prefabs_in_work(db: Session, prefabs_in_work_id: int, prefabs_in_work: PrefabsInWorkUpdate):
    db_prefabs_in_work = get_prefabs_in_work(db, prefabs_in_work_id)
    if not db_prefabs_in_work:
        raise HTTPException(status_code=404, detail="PrefabsInWork not found")
    for key, value in prefabs_in_work.dict().items():
        setattr(db_prefabs_in_work, key, value)
    db.commit()
    db.refresh(db_prefabs_in_work)
    return db_prefabs_in_work

def delete_prefabs_in_work(db: Session, prefabs_in_work_id: int):
    db_prefabs_in_work = get_prefabs_in_work(db, prefabs_in_work_id)
    if not db_prefabs_in_work:
        raise HTTPException(status_code=404, detail="PrefabsInWork not found")
    db.delete(db_prefabs_in_work)
    db.commit()
    return db_prefabs_in_work

def get_warehouse(db: Session, warehouse_id: int):
    return db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()


def create_warehouse(db: Session, warehouse: WarehouseCreate):
    db_warehouse = Warehouse(**warehouse.dict())
    db.add(db_warehouse)
    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse


def update_warehouse(db: Session, warehouse_id: int, warehouse: WarehouseUpdate):
    db_warehouse = get_warehouse(db, warehouse_id)
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    for key, value in warehouse.dict().items():
        setattr(db_warehouse, key, value)
    db.commit()
    db.refresh(db_warehouse)
    return db_warehouse


def delete_warehouse(db: Session, warehouse_id: int):
    db_warehouse = get_warehouse(db, warehouse_id)
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    db.delete(db_warehouse)
    db.commit()
    return db_warehouse

def get_support_ticket(db: Session, ticket_id: int):
    return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

def create_support_ticket(db: Session, ticket: SupportTicketCreate):
    db_ticket = SupportTicket(**ticket.dict())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

def update_support_ticket(db: Session, ticket_id: int, ticket: SupportTicketUpdate):
    db_ticket = get_support_ticket(db, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="SupportTicket not found")
    for key, value in ticket.dict(exclude_unset=True).items():
        setattr(db_ticket, key, value)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

def get_support_tickets_by_status(db: Session, status: str):
    return db.query(SupportTicket).filter(SupportTicket.status == status).all()


# Routes
@app.post("/organizations/", response_model=OrganizationResponse)
def create_organization(organization: OrganizationCreate, db: Session = Depends(get_db)):
    db_organization = Organization(**organization.dict())
    db.add(db_organization)
    db.commit()
    db.refresh(db_organization)
    return db_organization


@app.get("/organizations/", response_model=List[OrganizationResponse])
def read_organizations(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    organizations = db.query(Organization).offset(skip).limit(limit).all()
    return organizations


@app.get("/organizations/{organization_id}", response_model=OrganizationResponse)
def read_organization(organization_id: int, db: Session = Depends(get_db)):
    organization = get_organization(db, organization_id=organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization

@app.put("/organizations/{organization_id}", response_model=OrganizationResponse)
def update_organization(organization_id: int, organization: OrganizationUpdate, db: Session = Depends(get_db)):
    db_organization = get_organization(db, organization_id=organization_id)
    if db_organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    for key, value in organization.dict().items():
        setattr(db_organization, key, value)

    db.commit()
    db.refresh(db_organization)
    return db_organization

@app.post("/users/", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, organization_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if organization_id is not None:
        query = query.filter(User.organization_id == organization_id)
    users = query.offset(skip).limit(limit).all()
    return users


@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = get_user(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/{chat_id}", response_model=UserResponse)
def read_user_by_chat_id(chat_id: Union[str, int], db: Session = Depends(get_db)):
    user = get_user_by_chat_id(db, chat_id=chat_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in user.dict().items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/chat/{chat_id}", response_model=UserResponse)
def read_user_by_chat_id(chat_id: Union[str, int], db: Session = Depends(get_db)):
    user = get_user_by_chat_id(db, chat_id=chat_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
@app.post("/worktypes/", response_model=WorkTypeResponse)
def create_work_type(work_type: WorkTypeCreate, db: Session = Depends(get_db)):
    db_work_type = WorkType(**work_type.dict())
    db.add(db_work_type)
    db.commit()
    db.refresh(db_work_type)
    return db_work_type


# CRUD operation для получения WorkType по списку ID
def get_worktypes_by_ids(db: Session, ids: List[int]):
    return db.query(WorkType).filter(WorkType.id.in_(ids)).all()

@app.get("/worktypes/", response_model=List[WorkTypeResponse])
def read_work_types(ids: List[int] = Query(None), db: Session = Depends(get_db)):
    if ids:
        work_types = get_worktypes_by_ids(db, ids)
    else:
        work_types = db.query(WorkType).all()
    return work_types


@app.get("/worktypes/{work_type_id}", response_model=WorkTypeResponse)
def read_work_type(work_type_id: int, db: Session = Depends(get_db)):
    work_type = get_work_type(db, work_type_id=work_type_id)
    if work_type is None:
        raise HTTPException(status_code=404, detail="WorkType not found")
    return work_type


@app.post("/objects/", response_model=ObjectResponse)
def create_object(object: ObjectCreate, db: Session = Depends(get_db)):
    db_object = Object(**object.dict())
    db.add(db_object)
    db.commit()
    db.refresh(db_object)
    return db_object

@app.put("/objects/{object_id}", response_model=ObjectResponse)
def update_object(object_id: int, object: ObjectUpdate, db: Session = Depends(get_db)):
    db_object = get_object(db, object_id=object_id)
    if db_object is None:
        raise HTTPException(status_code=404, detail="Object not found")

    for key, value in object.dict().items():
        setattr(db_object, key, value)

    db.commit()
    db.refresh(db_object)
    return db_object

@app.get("/objects/", response_model=List[ObjectResponse])
def read_objects(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    objects = db.query(Object).offset(skip).limit(limit).all()
    return objects


@app.get("/objects/{object_id}", response_model=ObjectResponse)
def read_object(object_id: int, db: Session = Depends(get_db)):
    object = get_object(db, object_id=object_id)
    if object is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return object

@app.get("/objects/{object_id}/blocksections/", response_model=List[BlockSectionResponse])
def read_block_sections_by_object(object_id: int, db: Session = Depends(get_db)):
    object = get_object(db, object_id=object_id)
    if object is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return object.block_sections
@app.post("/blocksections/", response_model=BlockSectionResponse)
def create_block_section(block_section: BlockSectionCreate, db: Session = Depends(get_db)):
    db_block_section = BlockSection(**block_section.dict())
    db.add(db_block_section)
    db.commit()
    db.refresh(db_block_section)
    return db_block_section


@app.get("/blocksections/", response_model=List[BlockSectionResponse])
def read_block_sections(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    block_sections = db.query(BlockSection).offset(skip).limit(limit).all()
    return block_sections


@app.get("/blocksections/{block_section_id}", response_model=BlockSectionResponse)
def read_block_section(block_section_id: int, db: Session = Depends(get_db)):
    block_section = get_block_section(db, block_section_id=block_section_id)
    if block_section is None:
        raise HTTPException(status_code=404, detail="BlockSection not found")
    return block_section


@app.get("/objects/{object_id}/block_sections/", response_model=List[BlockSectionResponse])
def read_block_sections_by_object(object_id: int, db: Session = Depends(get_db)):
    object = get_object(db, object_id=object_id)
    if object is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return object.block_sections


@app.post("/fronttransfers/", response_model=FrontTransferResponse)
def create_front_transfer(front_transfer: FrontTransferCreate, db: Session = Depends(get_db)):
    db_front_transfer = FrontTransfer(**front_transfer.dict())
    db.add(db_front_transfer)
    db.commit()
    db.refresh(db_front_transfer)
    return db_front_transfer


@app.get("/fronttransfers/", response_model=List[FrontTransferResponse])
def read_front_transfers(skip: int = 0, limit: int = 10, status: Optional[str] = None, db: Session = Depends(get_db)):
    if status:
        front_transfers = db.query(FrontTransfer).filter(FrontTransfer.status == status).offset(skip).limit(limit).all()
    else:
        front_transfers = db.query(FrontTransfer).offset(skip).limit(limit).all()
    return front_transfers


@app.get("/fronttransfers/{front_transfer_id}", response_model=FrontTransferResponse)
def read_front_transfer(front_transfer_id: int, db: Session = Depends(get_db)):
    front_transfer = get_front_transfer(db, front_transfer_id=front_transfer_id)
    if front_transfer is None:
        raise HTTPException(status_code=404, detail="FrontTransfer not found")
    return front_transfer


@app.put("/fronttransfers/{front_transfer_id}", response_model=FrontTransferResponse)
def update_front_transfer(front_transfer_id: int, front_transfer: FrontTransferUpdate, db: Session = Depends(get_db)):
    db_front_transfer = get_front_transfer(db, front_transfer_id=front_transfer_id)
    if db_front_transfer is None:
        raise HTTPException(status_code=404, detail="FrontTransfer not found")

    for key, value in front_transfer.dict().items():
        setattr(db_front_transfer, key, value)

    db.commit()
    db.refresh(db_front_transfer)
    return db_front_transfer


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    file_location = f"files/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    return {"info": "file saved successfully"}




@app.post("/frontworkforces/", response_model=FrontWorkforceResponse)
def create_front_workforce(front_workforce: FrontWorkforceCreate, db: Session = Depends(get_db)):
    db_front_workforce = FrontWorkforce(**front_workforce.dict())
    db.add(db_front_workforce)
    db.commit()
    db.refresh(db_front_workforce)
    return db_front_workforce


@app.get("/frontworkforces/", response_model=List[FrontWorkforceResponse])
def read_front_workforces(skip: int = 0, db: Session = Depends(get_db)):
    front_workforces = db.query(FrontWorkforce).offset(skip).all()
    return front_workforces


@app.get("/frontworkforces/{front_workforce_id}", response_model=FrontWorkforceResponse)
def read_front_workforce(front_workforce_id: int, db: Session = Depends(get_db)):
    front_workforce = db.query(FrontWorkforce).filter(FrontWorkforce.id == front_workforce_id).first()
    if front_workforce is None:
        raise HTTPException(status_code=404, detail="FrontWorkforce not found")
    return front_workforce


@app.patch("/frontworkforces/{front_workforce_id}", response_model=FrontWorkforceResponse)
def update_front_workforce(front_workforce_id: int, front_workforce: FrontWorkforceUpdate,
                           db: Session = Depends(get_db)):
    db_front_workforce = db.query(FrontWorkforce).filter(FrontWorkforce.id == front_workforce_id).first()
    if db_front_workforce is None:
        raise HTTPException(status_code=404, detail="FrontWorkforce not found")

    for key, value in front_workforce.dict(exclude_unset=True).items():
        setattr(db_front_workforce, key, value)

    db.commit()
    db.refresh(db_front_workforce)
    return db_front_workforce

@app.delete("/frontworkforces/{front_workforce_id}", response_model=FrontWorkforceResponse)
def delete_front_workforce(front_workforce_id: int, db: Session = Depends(get_db)):
    front_workforce = db.query(FrontWorkforce).filter(FrontWorkforce.id == front_workforce_id).first()
    if front_workforce is None:
        raise HTTPException(status_code=404, detail="FrontWorkforce not found")
    db.delete(front_workforce)
    db.commit()
    return front_workforce

@app.post("/volumes/", response_model=VolumeResponse, status_code=201)
def create_volume(volume: VolumeCreate, db: Session = Depends(get_db)):
    db_volume = Volume(**volume.dict())
    db.add(db_volume)
    db.commit()
    db.refresh(db_volume)
    return db_volume


@app.get("/volumes/", response_model=List[VolumeResponse])
def read_volumes(skip: int = 0, db: Session = Depends(get_db)):
    volumes = db.query(Volume).offset(skip).all()
    return volumes


@app.get("/volumes/{volume_id}", response_model=VolumeResponse)
def read_volume(volume_id: int, db: Session = Depends(get_db)):
    volume = get_volume(db, volume_id=volume_id)
    if volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    return volume



@app.patch("/volumes/{volume_id}", response_model=VolumeResponse)
def patch_volume(volume_id: int, volume: VolumeUpdate, db: Session = Depends(get_db)):
    db_volume = get_volume(db, volume_id=volume_id)
    if db_volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")

    for key, value in volume.dict(exclude_unset=True).items():
        setattr(db_volume, key, value)

    db.commit()
    db.refresh(db_volume)
    return db_volume

@app.put("/volumes/{volume_id}", response_model=VolumeResponse)
def update_volume(volume_id: int, volume: VolumeUpdate, db: Session = Depends(get_db)):
    db_volume = get_volume(db, volume_id=volume_id)
    if db_volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")

    for key, value in volume.dict().items():
        setattr(db_volume, key, value)

    db.commit()
    db.refresh(db_volume)
    return db_volume


@app.delete("/volumes/{volume_id}", response_model=VolumeResponse)
def delete_volume(volume_id: int, db: Session = Depends(get_db)):
    volume = get_volume(db, volume_id=volume_id)
    if volume is None:
        raise HTTPException(status_code=404, detail="Volume not found")
    db.delete(volume)
    db.commit()
    return volume



@app.post("/prefab_types/", response_model=PrefabTypeResponse, status_code=201)
def create_prefab_type(prefab_type: PrefabTypeCreate, db: Session = Depends(get_db)):
    return create_prefab_type(db, prefab_type)

@app.get("/prefab_types/", response_model=List[PrefabTypeResponse])
def read_prefab_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    prefab_types = db.query(PrefabType).offset(skip).limit(limit).all()
    return prefab_types


@app.get("/prefab_types/{prefab_type_id}", response_model=PrefabTypeResponse)
def read_prefab_type(prefab_type_id: int, db: Session = Depends(get_db)):
    db_prefab_type = get_prefab_type(db, prefab_type_id)
    if not db_prefab_type:
        raise HTTPException(status_code=404, detail="PrefabType not found")
    return db_prefab_type


@app.put("/prefab_types/{prefab_type_id}", response_model=PrefabTypeResponse)
def update_prefab_type(prefab_type_id: int, prefab_type: PrefabTypeUpdate, db: Session = Depends(get_db)):
    return update_prefab_type(db, prefab_type_id, prefab_type)


@app.delete("/prefab_types/{prefab_type_id}", response_model=PrefabTypeResponse)
def delete_prefab_type(prefab_type_id: int, db: Session = Depends(get_db)):
    return delete_prefab_type(db, prefab_type_id)


@app.post("/prefabs/", response_model=PrefabResponse, status_code=201)
def create_prefab(prefab: PrefabCreate, db: Session = Depends(get_db)):
    return create_prefab(db, prefab)


@app.get("/prefabs/{prefab_id}", response_model=PrefabResponse)
def read_prefab(prefab_id: int, db: Session = Depends(get_db)):
    db_prefab = get_prefab(db, prefab_id)
    if not db_prefab:
        raise HTTPException(status_code=404, detail="Prefab not found")
    return db_prefab


@app.put("/prefabs/{prefab_id}", response_model=PrefabResponse)
def update_prefab(prefab_id: int, prefab: PrefabUpdate, db: Session = Depends(get_db)):
    return update_prefab(db, prefab_id, prefab)


@app.patch("/prefabs/{prefab_id}", response_model=PrefabResponse)
def patch_prefab(prefab_id: int, prefab: PrefabUpdate, db: Session = Depends(get_db)):
    db_prefab = get_prefab(db, prefab_id)
    if not db_prefab:
        raise HTTPException(status_code=404, detail="Prefab not found")
    for key, value in prefab.dict(exclude_unset=True).items():
        setattr(db_prefab, key, value)
    db.commit()
    db.refresh(db_prefab)
    return db_prefab


@app.delete("/prefabs/{prefab_id}", response_model=PrefabResponse)
def delete_prefab(prefab_id: int, db: Session = Depends(get_db)):
    return delete_prefab(db, prefab_id)


@app.post("/prefabs_in_work/", response_model=PrefabsInWorkResponse, status_code=201)
def create_prefabs_in_work_endpoint(prefabs_in_work: PrefabsInWorkCreate, db: Session = Depends(get_db)):
    return create_prefabs_in_work(db, prefabs_in_work)

@app.get("/prefabs_in_work/", response_model=List[PrefabsInWorkResponse])
def read_prefabs_in_work(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    prefabs_in_work = db.query(PrefabsInWork).offset(skip).limit(limit).all()
    return prefabs_in_work
@app.get("/prefabs_in_work/{prefabs_in_work_id}", response_model=PrefabsInWorkResponse)
def read_prefabs_in_work(prefabs_in_work_id: int, db: Session = Depends(get_db)):
    db_prefabs_in_work = get_prefabs_in_work(db, prefabs_in_work_id)
    if not db_prefabs_in_work:
        raise HTTPException(status_code=404, detail="PrefabsInWork not found")
    return db_prefabs_in_work

@app.put("/prefabs_in_work/{prefabs_in_work_id}", response_model=PrefabsInWorkResponse)
def update_prefabs_in_work_endpoint(prefabs_in_work_id: int, prefabs_in_work: PrefabsInWorkUpdate, db: Session = Depends(get_db)):
    db_prefabs_in_work = get_prefabs_in_work(db, prefabs_in_work_id)
    if not db_prefabs_in_work:
        raise HTTPException(status_code=404, detail="PrefabsInWork not found")

    for key, value in prefabs_in_work.dict(exclude_unset=True).items():
        if key != 'prefab_id':  # Исключаем обновление prefab_id
            setattr(db_prefabs_in_work, key, value)

    db.commit()
    db.refresh(db_prefabs_in_work)
    return db_prefabs_in_work


@app.patch("/prefabs_in_work/{prefabs_in_work_id}", response_model=PrefabsInWorkResponse)
def patch_prefabs_in_work_endpoint(prefabs_in_work_id: int, prefabs_in_work: PrefabsInWorkUpdate, db: Session = Depends(get_db)):
    db_prefabs_in_work = get_prefabs_in_work(db, prefabs_in_work_id)
    if not db_prefabs_in_work:
        raise HTTPException(status_code=404, detail="PrefabsInWork not found")

    try:
        update_data = prefabs_in_work.dict(exclude_unset=True)
        print(f"Updating PrefabsInWork ID: {prefabs_in_work_id} with data: {update_data}")  # Логирование данных

        for key, value in update_data.items():
            setattr(db_prefabs_in_work, key, value)

        db.commit()
        db.refresh(db_prefabs_in_work)
        return db_prefabs_in_work

    except ValidationError as e:
        print(f"Validation error: {e.json()}")
        raise HTTPException(status_code=422, detail=e.errors())



@app.delete("/prefabs_in_work/{prefabs_in_work_id}", response_model=PrefabsInWorkResponse)
def delete_prefabs_in_work_endpoint(prefabs_in_work_id: int, db: Session = Depends(get_db)):
    return delete_prefabs_in_work(db, prefabs_in_work_id)


@app.put("/prefabs_in_work/{prefabs_in_work_id}", response_model=PrefabsInWorkResponse)
def update_prefabs_in_work_endpoint(prefabs_in_work_id: int, prefabs_in_work: PrefabsInWorkUpdate,
                                    db: Session = Depends(get_db)):
    db_prefabs_in_work = get_prefabs_in_work(db, prefabs_in_work_id)
    if not db_prefabs_in_work:
        raise HTTPException(status_code=404, detail="PrefabsInWork not found")

    for key, value in prefabs_in_work.dict().items():
        setattr(db_prefabs_in_work, key, value)

    db.commit()
    db.refresh(db_prefabs_in_work)
    return db_prefabs_in_work

@app.get("/prefab_subtypes/", response_model=List[PrefabSubtypeResponse])
def read_prefab_subtypes(prefab_type_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(PrefabSubtype)
    if prefab_type_id:
        query = query.filter(PrefabSubtype.prefabtype_id == prefab_type_id)
    prefab_subtypes = query.offset(skip).limit(limit).all()
    return prefab_subtypes


@app.get("/prefab_subtypes/{prefab_subtype_id}", response_model=PrefabSubtypeResponse)
def read_prefab_subtype(prefab_subtype_id: int, db: Session = Depends(get_db)):
    db_prefab_subtype = db.query(PrefabSubtype).filter(PrefabSubtype.id == prefab_subtype_id).first()
    if not db_prefab_subtype:
        raise HTTPException(status_code=404, detail="PrefabSubtype not found")
    return db_prefab_subtype

@app.get("/prefabs/", response_model=List[PrefabResponse])
def read_prefabs(prefab_type_id: Optional[int] = None, prefab_subtype_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Prefab)
    if prefab_type_id:
        query = query.filter(Prefab.prefab_type_id == prefab_type_id)
    if prefab_subtype_id:
        query = query.filter(Prefab.prefab_subtype_id == prefab_subtype_id)
    prefabs = query.offset(skip).limit(limit).all()
    return prefabs


@app.get("/prefabs/{prefab_id}", response_model=PrefabResponse)
def read_prefab(prefab_id: int, db: Session = Depends(get_db)):
    db_prefab = db.query(Prefab).filter(Prefab.id == prefab_id).first()
    if not db_prefab:
        raise HTTPException(status_code=404, detail="Prefab not found")
    return db_prefab


@app.post("/warehouses/", response_model=WarehouseResponse, status_code=201)
def create_warehouse_endpoint(warehouse: WarehouseCreate, db: Session = Depends(get_db)):
    return create_warehouse(db, warehouse)


@app.get("/warehouses/", response_model=List[WarehouseResponse])
def read_warehouses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    warehouses = db.query(Warehouse).offset(skip).limit(limit).all()
    return warehouses


@app.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def read_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    db_warehouse = get_warehouse(db, warehouse_id)
    if not db_warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return db_warehouse


@app.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse_endpoint(warehouse_id: int, warehouse: WarehouseUpdate, db: Session = Depends(get_db)):
    return update_warehouse(db, warehouse_id, warehouse)


@app.delete("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def delete_warehouse_endpoint(warehouse_id: int, db: Session = Depends(get_db)):
    return delete_warehouse(db, warehouse_id)

@app.post("/support_tickets/", response_model=SupportTicketResponse, status_code=201)
def create_support_ticket_endpoint(ticket: SupportTicketCreate, db: Session = Depends(get_db)):
    return create_support_ticket(db, ticket)

@app.get("/support_tickets/", response_model=List[SupportTicketResponse])
def read_support_tickets(status: Optional[str] = None, db: Session = Depends(get_db)):
    if status:
        return get_support_tickets_by_status(db, status)
    return db.query(SupportTicket).all()

@app.get("/support_tickets/{ticket_id}", response_model=SupportTicketResponse)
def read_support_ticket(ticket_id: int, db: Session = Depends(get_db)):
    db_ticket = get_support_ticket(db, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="SupportTicket not found")
    return db_ticket

@app.put("/support_tickets/{ticket_id}", response_model=SupportTicketResponse)
def update_support_ticket_endpoint(ticket_id: int, ticket: SupportTicketUpdate, db: Session = Depends(get_db)):
    return update_support_ticket(db, ticket_id, ticket)


@app.patch("/support_tickets/{ticket_id}", response_model=SupportTicketResponse)
def update_support_ticket(ticket_id: int, ticket: SupportTicketUpdate, db: Session = Depends(get_db)):
    db_ticket = get_support_ticket(db, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="SupportTicket not found")

    update_data = ticket.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_ticket, key, value)

    db.commit()
    db.refresh(db_ticket)
    return db_ticket


# Запуск FastAPI
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)