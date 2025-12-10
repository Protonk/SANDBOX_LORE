#pragma D option quiet
syscall::read:entry
{
    printf("EVENT target_symbol=%s mpc=%p handlep=%p xd=%p\n", probefunc, arg0, arg1, arg2);
    exit(0);
}
