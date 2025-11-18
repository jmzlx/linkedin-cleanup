"""
Connection Remover - Utilities for removing LinkedIn connections.
"""
from typing import Optional, Tuple

from linkedin_cleanup import config
from linkedin_cleanup.linkedin_client import LinkedInClient


async def find_more_button(client: LinkedInClient) -> Optional[object]:
    """Find the 'More' button (three dots) in the profile section."""
    page = client.page
    print("    → Looking for 'More' button (three dots)...")
    for selector in config.MORE_BUTTON_SELECTORS:
        try:
            button = page.locator(selector).first
            if await button.is_visible(timeout=config.SHORT_SELECTOR_TIMEOUT):
                print("    ✓ Found 'More' button")
                return button
        except Exception:
            continue
    print("    ✗ Could not find 'More' button")
    return None


async def find_remove_connection_option(client: LinkedInClient) -> Optional[object]:
    """Find the 'Remove connection' option in the dropdown menu - tested and working selector."""
    page = client.page
    print("    → Looking for 'Remove connection' option in dropdown...")
    try:
        locator = page.locator(config.REMOVE_CONNECTION_SELECTOR)
        # Check if element exists (don't rely on is_visible as these may not pass visibility check)
        if await locator.count() > 0:
            print("    ✓ Found 'Remove connection' option")
            return locator.first
    except Exception:
        pass
    print("    ✗ Could not find 'Remove connection' option")
    return None


async def remove_connection(
    client: LinkedInClient,
    url: str,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """Remove a single connection. Returns (success, message)."""
    page = client.page
    try:
        # Navigate to profile
        print(f"    → Navigating to profile: {url}")
        await client.navigate_to(url)
        print("    ✓ Profile page loaded")
        
        # Find and click "More" button
        more_button = await find_more_button(client)
        if not more_button:
            return False, "Could not find 'More' button"
        
        print("    → Clicking 'More' button...")
        await client.human_like_click(more_button)
        print("    ✓ Clicked 'More' button")
        
        # Wait for dropdown to appear
        print("    → Waiting for dropdown menu to appear...")
        try:
            await page.wait_for_selector(
                config.DROPDOWN_CONTENT_SELECTOR,
                timeout=config.VERIFICATION_TIMEOUT
            )
            print("    ✓ Dropdown menu appeared")
        except Exception:
            print("    ⚠ Dropdown selector not found, continuing anyway...")
            pass  # Continue even if not found
        
        await client.random_delay(1, 2)
        
        # Find "Remove connection" option
        remove_option = await find_remove_connection_option(client)
        if not remove_option:
            # Try pressing Escape to close dropdown and retry
            print("    → Closing dropdown and retrying...")
            await page.keyboard.press("Escape")
            await client.random_delay(0.5, 1)
            return False, "Could not find 'Remove connection' option"
        
        # DRY RUN MODE: Stop here and report success
        if dry_run:
            aria_label = await remove_option.get_attribute("aria-label")
            print(f"    ✓ [DRY RUN] Found remove option with aria-label: {aria_label}")
            # Close dropdown
            print("    → Closing dropdown...")
            await page.keyboard.press("Escape")
            return True, "[DRY RUN] Successfully found all selectors - would remove connection"
        
        # LIVE MODE: Actually remove the connection
        print("    → Clicking 'Remove connection' option...")
        await remove_option.scroll_into_view_if_needed()
        
        try:
            await remove_option.click(force=True)
            print("    ✓ Clicked 'Remove connection'")
        except Exception:
            # Fallback to JavaScript click if regular click fails
            print("    → Regular click failed, trying JavaScript click...")
            await page.evaluate(
                "arguments[0].click();",
                await remove_option.element_handle()
            )
            print("    ✓ JavaScript click successful")
        
        # Wait for the removal to process (LinkedIn may open popups/redirects)
        print("    → Waiting for removal to process...")
        await client.random_delay(2, 3)
        
        # Close any new tabs that LinkedIn may have opened (e.g., jobs page)
        print("    → Checking for and closing any unwanted new tabs...")
        await client.close_new_tabs(keep_url_pattern="linkedin.com/in/")
        
        # Navigate back to the profile URL to verify removal
        print("    → Navigating back to profile to verify removal...")
        await client.navigate_to(url)
        
        # Verify removal by checking for Connect button (appears after disconnection)
        print("    → Verifying removal (checking for Connect button)...")
        connect_button = page.locator(config.CONNECT_BUTTON_SELECTOR).first
        connect_visible = await connect_button.is_visible(
            timeout=config.VERIFICATION_TIMEOUT
        )
        
        # Also check if "More" button is gone (indicates connection removed)
        print("    → Verifying removal (checking if More button is gone)...")
        more_button_after = await find_more_button(client)
        
        # Multiple verification checks
        if connect_visible:
            # Double-check: verify the Connect button is actually visible and clickable
            try:
                connect_text = await connect_button.inner_text()
                if "Connect" in connect_text:
                    print("    ✓ Verification successful: Connect button visible")
                    return True, "Successfully removed (Connect button visible)"
            except Exception:
                pass
        
        if not more_button_after:
            print("    ✓ Verification successful: More button no longer visible")
            return True, "Successfully removed (More button no longer visible)"
        
        # If neither check passed, the removal may have failed
        print("    ✗ Verification failed: Connect button not found and More button still present")
        return False, (
            "Removal verification failed - Connect button not found "
            "and More button still present"
        )
    
    except Exception as e:
        print(f"    ✗ Error during removal: {str(e)}")
        return False, f"Error: {str(e)}"

