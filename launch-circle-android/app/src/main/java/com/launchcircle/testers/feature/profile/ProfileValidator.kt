package com.launchcircle.testers.feature.profile

object ProfileValidator {
    fun isTesterEmailValid(value: String): Boolean {
        val email = value.trim()
        return email.contains('@') && email.substringAfter('@').contains('.') && !email.contains(' ')
    }

    fun isReady(country: String, languages: List<String>, testerEmail: String, consent: Boolean): Boolean {
        return country.trim().length == 2 &&
            languages.isNotEmpty() &&
            isTesterEmailValid(testerEmail) &&
            consent
    }
}
