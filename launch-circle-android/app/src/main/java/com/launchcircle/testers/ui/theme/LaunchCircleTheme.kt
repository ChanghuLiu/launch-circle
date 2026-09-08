package com.launchcircle.testers.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

val LaunchSuccess = Color(0xFF16845B)
val LaunchAttention = Color(0xFFB86B00)

private val LightColors = lightColorScheme(
    primary = Color(0xFF1859D1),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDCE6FF),
    onPrimaryContainer = Color(0xFF092B68),
    secondary = Color(0xFF485D86),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFDCE6FA),
    onSecondaryContainer = Color(0xFF263957),
    tertiary = LaunchSuccess,
    onTertiary = Color.White,
    tertiaryContainer = Color(0xFFC1F2D9),
    onTertiaryContainer = Color(0xFF075137),
    error = Color(0xFFBA1A1A),
    onError = Color.White,
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF93000A),
    background = Color(0xFFF7F9FD),
    onBackground = Color(0xFF171C24),
    surface = Color(0xFFF7F9FD),
    onSurface = Color(0xFF171C24),
    surfaceVariant = Color(0xFFE1E6EF),
    onSurfaceVariant = Color(0xFF424751),
    surfaceContainerLowest = Color.White,
    surfaceContainerLow = Color(0xFFF1F4FA),
    surfaceContainer = Color(0xFFEBEEF4),
    surfaceContainerHigh = Color(0xFFE5E8EE),
    outline = Color(0xFF737781),
    outlineVariant = Color(0xFFC3C6CF),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFADC6FF),
    onPrimary = Color(0xFF002E69),
    primaryContainer = Color(0xFF064397),
    onPrimaryContainer = Color(0xFFD8E2FF),
    secondary = Color(0xFFB7C8E9),
    onSecondary = Color(0xFF21324C),
    secondaryContainer = Color(0xFF374966),
    onSecondaryContainer = Color(0xFFD7E3FF),
    tertiary = Color(0xFF73DBAC),
    onTertiary = Color(0xFF003824),
    tertiaryContainer = Color(0xFF005236),
    onTertiaryContainer = Color(0xFF90F8C7),
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    background = Color(0xFF0F141B),
    onBackground = Color(0xFFE1E6EF),
    surface = Color(0xFF0F141B),
    onSurface = Color(0xFFE1E6EF),
    surfaceVariant = Color(0xFF424751),
    onSurfaceVariant = Color(0xFFC3C6CF),
    surfaceContainerLowest = Color(0xFF0A0F15),
    surfaceContainerLow = Color(0xFF171C24),
    surfaceContainer = Color(0xFF1B2028),
    surfaceContainerHigh = Color(0xFF262A32),
    outline = Color(0xFF8D919B),
    outlineVariant = Color(0xFF424751),
)

private val LaunchTypography = Typography(
    displayLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 52.sp,
        lineHeight = 58.sp,
        letterSpacing = (-1.2).sp,
    ),
    displayMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 42.sp,
        lineHeight = 48.sp,
        letterSpacing = (-0.8).sp,
    ),
    displaySmall = TextStyle(fontWeight = FontWeight.Bold, fontSize = 34.sp, lineHeight = 40.sp),
    headlineLarge = TextStyle(fontWeight = FontWeight.Bold, fontSize = 30.sp, lineHeight = 38.sp),
    headlineMedium = TextStyle(fontWeight = FontWeight.Bold, fontSize = 26.sp, lineHeight = 34.sp),
    headlineSmall = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 22.sp, lineHeight = 29.sp),
    titleLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 20.sp, lineHeight = 27.sp),
    titleMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 23.sp),
    titleSmall = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontSize = 13.sp, lineHeight = 19.sp),
    labelLarge = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp),
    labelMedium = TextStyle(fontWeight = FontWeight.SemiBold, fontSize = 12.sp, lineHeight = 17.sp, letterSpacing = 0.4.sp),
    labelSmall = TextStyle(fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 17.sp, letterSpacing = 0.4.sp),
)

private val LaunchShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(22.dp),
    extraLarge = RoundedCornerShape(28.dp),
)

@Composable
fun LaunchCircleTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = LaunchTypography,
        shapes = LaunchShapes,
        content = content,
    )
}
