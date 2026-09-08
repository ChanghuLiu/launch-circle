# Launch Circle Retrofit/Gson wire models.
#
# Production versionCode 2 proved that R8 renamed GoogleAuthRequest.id_token
# to "a" in the actual HTTP JSON body.
#
# Preserve all API model classes and members so Retrofit/Gson request and
# response wire names remain stable in minified release builds.
-keep class com.launchcircle.testers.core.model.** { *; }

# Preserve runtime metadata used by Gson/Retrofit.
-keepattributes RuntimeVisibleAnnotations,RuntimeInvisibleAnnotations,AnnotationDefault,Signature
