# NetScope Networks API

"""
API endpoints for network management.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.network import Network, Subnet
from app.schemas.network import (
    Network as NetworkSchema,
    NetworkCreate,
    NetworkUpdate,
    Subnet as SubnetSchema
)

router = APIRouter()


@router.get("/networks", response_model=List[NetworkSchema])
async def list_networks(
    db: AsyncSession = Depends(get_async_session)
):
    """List all configured networks."""
    result = await db.execute(select(Network))
    return list(result.scalars().all())


@router.post("/networks", response_model=NetworkSchema)
async def create_network(
    network: NetworkCreate,
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new network configuration."""
    db_network = Network(**network.model_dump(exclude_unset=True))
    db.add(db_network)
    await db.commit()
    await db.refresh(db_network)
    return db_network


@router.get("/networks/{network_id}", response_model=NetworkSchema)
async def get_network(
    network_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific network."""
    result = await db.execute(
        select(Network).where(Network.id == network_id)
    )
    network = result.scalar_one_or_none()
    
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    return network


@router.put("/networks/{network_id}", response_model=NetworkSchema)
async def update_network(
    network_id: int,
    network: NetworkUpdate,
    db: AsyncSession = Depends(get_async_session)
):
    """Update a network configuration."""
    result = await db.execute(
        select(Network).where(Network.id == network_id)
    )
    db_network = result.scalar_one_or_none()
    
    if not db_network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    for field, value in network.model_dump(exclude_unset=True).items():
        setattr(db_network, field, value)
    
    await db.commit()
    await db.refresh(db_network)
    return db_network


@router.delete("/networks/{network_id}")
async def delete_network(
    network_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Delete a network configuration."""
    result = await db.execute(
        select(Network).where(Network.id == network_id)
    )
    network = result.scalar_one_or_none()
    
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    await db.delete(network)
    await db.commit()
    
    return {"message": "Network deleted successfully"}


@router.get("/networks/{network_id}/subnets", response_model=List[SubnetSchema])
async def list_subnets(
    network_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """List subnets for a network."""
    result = await db.execute(
        select(Subnet).where(Subnet.network_id == network_id)
    )
    return list(result.scalars().all())


@router.post("/networks/{network_id}/subnets", response_model=SubnetSchema)
async def create_subnet(
    network_id: int,
    subnet: SubnetSchema,
    db: AsyncSession = Depends(get_async_session)
):
    """Create a subnet."""
    result = await db.execute(
        select(Network).where(Network.id == network_id)
    )
    db_network = result.scalar_one_or_none()
    
    if not db_network:
        raise HTTPException(status_code=404, detail="Network not found")
    
    db_subnet = Subnet(**subnet.model_dump(), network_id=network_id)
    db.add(db_subnet)
    await db.commit()
    await db.refresh(db_subnet)
    return db_subnet
