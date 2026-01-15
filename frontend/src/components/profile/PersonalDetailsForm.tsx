'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import api from '@/lib/axios';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

const schema = z.object({
    address: z.string().optional(),
    blood_group: z.string().optional(),
    father_name: z.string().optional(),
    mother_name: z.string().optional(),
    spouse_name: z.string().optional(),
    emergency_contact_name: z.string().optional(),
    emergency_contact_phone: z.string().optional(),
    dob: z.string().optional(),
    permanent_address: z.string().optional(),
    children_names: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function PersonalDetailsForm() {
    const { user, fetchUser } = useAuth();
    const [isLoading, setIsLoading] = useState(false);

    const {
        register,
        handleSubmit,
        reset,
        watch,
        setValue,
        getValues,
        formState: { errors }
    } = useForm<FormValues>({
        resolver: zodResolver(schema),
    });

    const [sameAsCurrent, setSameAsCurrent] = useState(false);

    // Watch address to update permanent if checked
    const currentAddress = watch('address');

    useEffect(() => {
        if (sameAsCurrent) {
            setValue('permanent_address', currentAddress);
        }
    }, [sameAsCurrent, currentAddress, setValue]);

    useEffect(() => {
        if (user) {
            reset({
                address: user.address || '',
                blood_group: user.blood_group || '',
                father_name: user.father_name || '',
                mother_name: user.mother_name || '',
                spouse_name: user.spouse_name || '',
                emergency_contact_name: user.emergency_contact_name || '',
                emergency_contact_phone: user.emergency_contact_phone || '',
                dob: user.dob || '',
                permanent_address: user.permanent_address || '',
                children_names: user.children_names || ''
            });

            // Check if same
            if (user.address && user.permanent_address && user.address === user.permanent_address) {
                setSameAsCurrent(true);
            }
        }
    }, [user, reset]);

    const onSubmit = async (data: FormValues) => {
        setIsLoading(true);
        try {
            await api.patch('/users/me', data);
            toast.success('Profile updated successfully');
            await fetchUser();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || 'Failed to update profile');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Personal Details</CardTitle>
                <CardDescription>Manage your personal information</CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">

                    {/* Bio */}
                    <div>
                        <h3 className="text-sm font-semibold mb-3">Bio</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="dob">Date of Birth</Label>
                                <Input type="date" id="dob" {...register('dob')} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="blood">Blood Group</Label>
                                <Input id="blood" placeholder="e.g. O+" {...register('blood_group')} />
                            </div>
                        </div>
                    </div>

                    {/* Contact */}
                    <div>
                        <h3 className="text-sm font-semibold mb-3">Contact</h3>
                        <div className="space-y-2">
                            <Label htmlFor="address">Current Address</Label>
                            <Textarea id="address" {...register('address')} placeholder="Full address" />
                        </div>
                    </div>


                    {/* Permanent Address */}
                    <div>
                        <div className="flex items-center space-x-2 mb-3">
                            <Checkbox
                                id="sameAs"
                                checked={sameAsCurrent}
                                onCheckedChange={(checked) => {
                                    setSameAsCurrent(checked === true);
                                    if (checked === true) setValue('permanent_address', getValues('address'));
                                }}
                            />
                            <Label htmlFor="sameAs" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                Permanent Address same as Current Address
                            </Label>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="p_address">Permanent Address</Label>
                            <Textarea
                                id="p_address"
                                {...register('permanent_address')}
                                placeholder="Permanent address"
                                disabled={sameAsCurrent}
                            />
                        </div>
                    </div>

                    {/* Family */}
                    <div>
                        <h3 className="text-sm font-semibold mb-3">Family</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="father">Father's Name</Label>
                                <Input id="father" {...register('father_name')} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="mother">Mother's Name</Label>
                                <Input id="mother" {...register('mother_name')} />
                            </div>
                            <div className="space-y-2 md:col-span-2">
                                <Label htmlFor="spouse">Spouse Name</Label>
                                <Input id="spouse" {...register('spouse_name')} />
                            </div>
                            <div className="space-y-2 md:col-span-2">
                                <Label htmlFor="children">Children's Name(s)</Label>
                                <Input id="children" {...register('children_names')} placeholder="Comma separated names" />
                            </div>
                        </div>
                    </div>

                    {/* Emergency */}
                    <div>
                        <h3 className="text-sm font-semibold mb-3">Emergency Contact</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="ename">Contact Name</Label>
                                <Input id="ename" {...register('emergency_contact_name')} />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="ephone">Phone Number</Label>
                                <Input id="ephone" {...register('emergency_contact_phone')} />
                            </div>
                        </div>
                    </div>

                    <Button type="submit" disabled={isLoading}>
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Changes
                    </Button>
                </form>
            </CardContent>
        </Card >
    );
}
