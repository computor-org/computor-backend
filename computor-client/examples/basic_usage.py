"""
Basic usage examples for Computor API Client.

This example demonstrates:
- Client initialization
- Authentication
- CRUD operations
- Error handling
"""

import asyncio
from computor_client import ComputorClient, ComputorAPIError
from computor_types.organizations import OrganizationCreate, OrganizationUpdate


async def main():
    """Main example function."""

    # Initialize client
    async with ComputorClient(base_url="http://localhost:8000") as client:
        try:
            # Authenticate
            print("🔐 Authenticating...")
            auth_response = await client.authenticate(
                username="admin",
                password="admin"
            )
            print(f"✅ Authenticated as {auth_response.get('username')}")
            print()

            # List organizations
            print("📋 Listing organizations...")
            organizations = await client.organizations.list()
            print(f"✅ Found {len(organizations)} organizations")
            for org in organizations[:3]:
                print(f"  • {org.name} (ID: {org.id})")
            print()

            # Create a new organization
            print("➕ Creating new organization...")
            new_org = await client.organizations.create(
                OrganizationCreate(
                    name="Example University",
                    description="An example organization created via API client",
                    gitlab_group_path="example-university",
                )
            )
            print(f"✅ Created organization: {new_org.name} (ID: {new_org.id})")
            print()

            # Get the organization by ID
            print(f"🔍 Fetching organization {new_org.id}...")
            fetched_org = await client.organizations.get(new_org.id)
            print(f"✅ Fetched: {fetched_org.name}")
            print()

            # Update the organization
            print(f"✏️  Updating organization {new_org.id}...")
            updated_org = await client.organizations.update(
                new_org.id,
                OrganizationUpdate(
                    description="Updated description via API client"
                )
            )
            print(f"✅ Updated description: {updated_org.description}")
            print()

            # Delete the organization
            print(f"🗑️  Deleting organization {new_org.id}...")
            await client.organizations.delete(new_org.id)
            print(f"✅ Deleted organization")

        except ComputorAPIError as e:
            print(f"❌ API Error: {e}")
            print(f"   Status: {e.status_code}")
            print(f"   Detail: {e.detail}")


if __name__ == "__main__":
    asyncio.run(main())
