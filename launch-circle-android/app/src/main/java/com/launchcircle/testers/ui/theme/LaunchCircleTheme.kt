package com.launchcircle.testers.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF2855D9),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDCE3FF),
    secondary = Color(0xFF4F5D92),
    secondaryContainer = Color(0xFFDDE2FF),
    surface = Color(0xFFFAF8FF),
    surfaceContainer = Color(0xFFF0F0FA),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFB6C4FF),
    onPrimary = Color(0xFF002A78),
    primaryContainer = Color(0xFF123B91),
    secondary = Color(0xFFBEC6F8),
    secondaryContainer = Color(0xFF37426B),
    surface = Color(0xFF121318),
    surfaceContainer = Color(0xFF1D1E25),
)

@Composable
fun LaunchCircleTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        content = content,
    )
}
