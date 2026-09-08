package com.launchcircle.testers

import com.google.gson.Gson
import com.launchcircle.testers.core.model.LaunchApp
import com.launchcircle.testers.core.model.LaunchCircle
import com.launchcircle.testers.core.model.LaunchInvite
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class CircleWireModelTest {
    private val gson = Gson()

    @Test
    fun appAndInviteWireModelsCarryCircleIdentityAndExpiry() {
        val app = gson.fromJson(
            """{
                "id":"app-1","owner_id":"owner-1","name":"Circle App",
                "package_name":"com.example.app","opt_in_url":"https://example.com",
                "google_group_url":null,"status":"WAITING_FOR_TESTERS",
                "tester_target":15,"testing_start_at":null,"testing_end_at":null,
                "circle_id":"circle-1"
            }""",
            LaunchApp::class.java,
        )
        val invite = gson.fromJson(
            """{
                "id":"invite-1","circle_id":"circle-1","invite_code":"LC-8H4K2",
                "status":"PENDING","share_url":"https://launchcircle.app/join/LC-8H4K2",
                "expires_at":"2026-08-27T12:00:00Z"
            }""",
            LaunchInvite::class.java,
        )

        assertEquals("circle-1", app.circle_id)
        assertEquals("circle-1", invite.circle_id)
        assertEquals("2026-08-27T12:00:00Z", invite.expires_at)
    }

    @Test
    fun circleWireModelPreservesActiveMemberDisplay() {
        val circle = gson.fromJson(
            """{
                "id":"circle-1","owner_id":"owner-1","name":"Owner's Launch Circle",
                "max_members":15,"active_member_count":2,
                "members":[
                    {"id":"member-1","user_id":"owner-1","display_name":"Owner",
                     "member_label":"Owner","role":"OWNER","status":"ACTIVE","joined_at":"2026-08-20T12:00:00Z"},
                    {"id":"member-2","user_id":"member-1","display_name":"Tester",
                     "member_label":"Tester","role":"MEMBER","status":"ACTIVE","joined_at":"2026-08-20T12:01:00Z"}
                ]
            }""",
            LaunchCircle::class.java,
        )

        assertNotNull(circle)
        assertEquals(15, circle.max_members)
        assertEquals(2, circle.active_member_count)
        assertEquals(listOf("Owner", "Tester"), circle.members.map { it.member_label })
    }
}
