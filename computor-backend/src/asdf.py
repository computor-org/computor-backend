import json
import asyncio
from computor_client import ComputorClient

if __name__ == "__main__":
    client = ComputorClient(
        base_url="http://localhost:8000"
    )

    async def asdf():
        erg = await client.login("course_manager","password")
        print(json.dumps(erg, indent=2))

        erg = await client.get("/students/course-contents?course_id=760f0765-deec-4ea2-9fd1-f8cd0f8ee037&path=unit_9")
        print(json.dumps(erg, indent=2))

        # erg = await client.get("/students/course-contents/961746ff-d157-4a18-9a3a-689f2e0dd0f4")
        # print(json.dumps(erg, indent=2))
    
    asyncio.run(asdf())

