#import <UserNotifications/UserNotifications.h>

@interface FeatherNotificationService : UNNotificationServiceExtension
@end

@implementation FeatherNotificationService

- (void)didReceiveNotificationRequest:(UNNotificationRequest *)request
                   withContentHandler:(void (^)(UNNotificationContent *))contentHandler {
    UNNotificationContent *original = request.content;
    id encryptedPayload = original.userInfo[@"p"];
    if (![encryptedPayload isKindOfClass:[NSString class]] || [encryptedPayload length] == 0) {
        contentHandler(original);
        return;
    }

    UNMutableNotificationContent *content = [original mutableCopy];
    NSString *language = [[NSLocale preferredLanguages] firstObject];
    content.title = @"Ghostgram";
    content.subtitle = @"";
    content.body = [language hasPrefix:@"ru"] ? @"Новое сообщение" : @"New message";
    contentHandler(content);
}

@end
