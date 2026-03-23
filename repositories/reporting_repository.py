from repositories.base_repository import BaseRepository

class ReportingRepository(BaseRepository):
    def member_summary(self, member_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT
                    COUNT(*) AS rounds_played,
                    COUNT(DISTINCT date_played) AS dates_played,
                    COUNT(DISTINCT course_id) AS courses_played
                FROM rounds
                WHERE member_id=?
                """,
                (member_id,),
            ).fetchone()
