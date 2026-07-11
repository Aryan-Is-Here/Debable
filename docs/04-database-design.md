# Database Design (Initial)

Tables

Users
- id
- username
- email
- avatar

Topics
- id
- title
- description
- creator_id
- status

DebateRooms
- id
- topic_id
- user1_id
- user2_id
- started_at
- ended_at

Messages
- id
- room_id
- sender_id
- content
- created_at

FactChecks
- id
- room_id
- requester_id
- claim
- verdict
- sources
- created_at

Ratings
- id
- room_id
- reviewer_id
- reviewed_user_id
- score
- comment
